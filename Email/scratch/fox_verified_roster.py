#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

def get_fox_roles():
    load_dotenv('/Users/mayankhinduja/Desktop/Demo/.env')
    pdl_key = os.environ.get("PDL_API_KEY")
    fallback_key = os.environ.get("PDL_API_KEY_FALLBACK")
    
    url = "https://api.peopledatalabs.com/v5/person/search"
    
    # Oct 2025 (6 month buffer)
    compliance_cutoff = "2025-10-22"
    
    # We broaden search to get a pool of 20, then we verify the top 5
    query = {
        "bool": {
            "must": [
                {"term": {"experience.company.name": "fox corporation"}},
                {"range": {"experience.end_date": {"gte": "2022-01-01", "lte": compliance_cutoff}}},
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
        "size": 25,
        "dataset": "resume"
    }

    keys = [pdl_key, fallback_key]
    data = None
    for k in keys:
        if not k: continue
        resp = requests.post(url, json=payload, headers={'X-Api-Key': k}, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            break
            
    if not data:
        print("❌ Search failed.")
        return

    print(f"\n--- 🦊 FOXA EXPERT POOL (Verified Old Roles) ---\n")
    results = []
    for record in data.get('data', []):
        fox_exp = [e for e in record.get('experience', []) if 'fox' in e.get('company', {}).get('name', '').lower()]
        if not fox_exp: continue
        
        # Sort experience by date to get the most recent Fox role
        fox_exp.sort(key=lambda x: x.get('end_date', '0000'), reverse=True)
        recent_fox = fox_exp[0]
        
        results.append({
            "name": record.get('full_name'),
            "fox_role": recent_fox.get('title'),
            "tenure": f"{recent_fox.get('start_date')} to {recent_fox.get('end_date')}",
            "linkedin": f"linkedin.com/in/{record.get('linkedin_username')}" if record.get('linkedin_username') else "N/A"
        })

    for i, r in enumerate(results):
        print(f"{i+1}. {r['name'].upper()}")
        print(f"   Old Role at Fox: {r['fox_role']}")
        print(f"   Tenure: {r['tenure']}")
        print(f"   LinkedIn: {r['linkedin']}")
        print("-" * 30)

if __name__ == "__main__":
    get_fox_roles()
