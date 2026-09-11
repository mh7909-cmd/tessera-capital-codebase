#!/usr/bin/env python3
import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

def final_foxa_bucket():
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    pdl_key = os.environ.get("PDL_API_KEY")
    
    url = "https://api.peopledatalabs.com/v5/person/search"
    
    # Oct 2025 (6 month buffer)
    compliance_cutoff = "2025-10-22"
    
    query = {
        "bool": {
            "must": [
                {"term": {"experience.company.name": "fox corporation"}},
                {"range": {"experience.end_date": {"gte": "2023-01-01", "lte": compliance_cutoff}}},
                {"exists": {"field": "work_email"}}
            ],
            "must_not": [
                {"term": {"job_company_name": "fox corporation"}},
                {"term": {"job_title": "engineer"}},
                {"term": {"job_title": "developer"}},
                {"term": {"job_title": "software"}}
            ]
        }
    }
    
    payload = {
        "query": query,
        "size": 20,
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
            print(f"\n--- 🦊 FINAL FOXA DATA BUCKET (2023-2025) ---\n")
            experts = []
            for record in data.get('data', []):
                fox_exps = [exp for exp in record.get('experience', []) if 'fox' in exp.get('company', {}).get('name', '').lower()]
                if fox_exps:
                    experts.append({
                        "name": record.get('full_name'),
                        "title": record.get('job_title'),
                        "fox_role": fox_exps[0].get('title'),
                        "tenure": f"{fox_exps[0].get('start_date')} to {fox_exps[0].get('end_date')}"
                    })
            
            for i, e in enumerate(experts):
                print(f"{i+1}. {e['name'].upper()}")
                print(f"   Role: {e['title']}")
                print(f"   Fox Tenure: {e['tenure']} ({e['fox_role']})")
                print("-" * 30)
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    final_foxa_bucket()
