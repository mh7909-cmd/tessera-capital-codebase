#!/usr/bin/env python3
import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

def verify_tenure_windows():
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    pdl_key = os.environ.get("PDL_API_KEY")
    
    url = "https://api.peopledatalabs.com/v5/person/search"
    
    # 1. Compliance Window: Oct 2025 (6 months ago from April 2026)
    compliance_cutoff = "2025-10-22"
    
    # 2. Target Window: 2023 to Oct 2025 (The tenure window the user wants)
    
    query = {
        "bool": {
            "must": [
                {"term": {"experience.company.name": "fox corporation"}},
                # Ensure they left Fox by the compliance cutoff
                {"range": {"experience.end_date": {"lte": compliance_cutoff}}},
                # Ensure they were there during or after 2023
                {"range": {"experience.end_date": {"gte": "2023-01-01"}}},
                {"exists": {"field": "work_email"}}
            ],
            "must_not": [
                {"term": {"job_company_name": "fox corporation"}},
                {"term": {"job_title": "engineer"}},
                {"term": {"job_title": "developer"}}
            ]
        }
    }
    
    payload = {
        "query": query,
        "size": 5,
        "dataset": "resume"
    }

    req_headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': pdl_key
    }
    
    try:
        resp = requests.post(url, json=payload, headers=req_headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n📊 Verified Experts for FOXA (Departure: 2023 - Oct 2025)\n")
            for record in data.get('data', []):
                # Find the Fox experience to show the exact dates
                fox_exps = [exp for exp in record.get('experience', []) if 'fox' in exp.get('company', {}).get('name', '').lower()]
                
                print(f"Name: {record.get('full_name')}")
                print(f"Role: {record.get('job_title')}")
                
                for exp in fox_exps:
                    start = exp.get('start_date', 'N/A')
                    end = exp.get('end_date', 'N/A')
                    print(f"   - Company: {exp.get('company', {}).get('name')} | Tenure: {start} to {end}")
                print("-" * 30)
        else:
            print(f"❌ PDL Error ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_tenure_windows()
