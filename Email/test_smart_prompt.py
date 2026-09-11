#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

def test_smart_prompt():
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    api_key = os.environ.get("NVIDIA_API_KEY")
    
    # Test cases to prove it's dynamic
    test_cases = [
        {"company": "Fox Corporation", "objective": "Analyze the impact of recent controversies and the Disney merger on advertising revenue."},
        {"company": "Align Technology", "objective": "Understand the adoption rate of clear aligners over traditional braces in private practices."},
        {"company": "CrowdStrike", "objective": "Determine the impact of the July outage on enterprise contract renewals and IT sentiment."}
    ]
    
    prompt_template = """You are a master intelligence analyst identifying the best human sources for primary diligence.
Given the target company and research objective, determine the absolute best profile of a person to interview.

TARGET COMPANY: {company}
OBJECTIVE: {objective}

Must return ONLY valid JSON with no markdown formatting. The JSON must match this structure exactly:
{{
    "strategy_type": "internal" | "external-customer" | "external-competitor" | "industry-expert",
    "target_companies": ["list", "of", "company names to search PDL for. if internal, use the target company. if external, describe the type of companies e.g. 'dental clinic'"],
    "target_titles": ["list", "of", "exact job titles"],
    "rationale": "Brief 1 sentence reason for this strategy"
}}"""

    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    for tc in test_cases:
        print(f"\n--- Testing: {tc['company']} ---")
        payload = {
            "model": "moonshotai/kimi-k2.5",
            "messages": [{"role": "user", "content": prompt_template.format(company=tc['company'], objective=tc['objective'])}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }
        
        try:
            req_headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
            resp = requests.post(url, json=payload, headers=req_headers, timeout=15)
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message'].get('content', '')
                print(content)
            else:
                print(f"Error: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_smart_prompt()
