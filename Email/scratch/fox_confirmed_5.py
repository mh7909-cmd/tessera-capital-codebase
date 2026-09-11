#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

def get_fox_big_5_backup():
    # Use the backup key precisely as verified
    pdl_key = '5bea6dd30237444911e843be0967d8e1e20ad1c99c988252e0ddf9277db995e4'
    url = "https://api.peopledatalabs.com/v5/person/search"
    
    # Oct 2025 (6 month buffer)
    compliance_cutoff = "2025-10-22"
    
    # Query for Fox departures in Strategy/Finance/Ops
    query = {
        "bool": {
            "must": [
                {"term": {"experience.company.name": "fox corporation"}},
                {"range": {"experience.end_date": {"gte": "2022-01-01", "lte": compliance_cutoff}}},
                {"bool": {
                    "should": [
                        {"term": {"experience.title": "strategy"}},
                        {"term": {"experience.title": "finance"}},
                        {"term": {"experience.title": "revenue"}},
                        {"term": {"experience.title": "advertising"}},
                        {"term": {"experience.title": "sales"}},
                        {"term": {"experience.title": "director"}},
                        {"term": {"experience.title": "manager"}},
                        {"term": {"experience.title": "vp"}}
                    ]
                }}
            ],
            "must_not": [
                {"term": {"job_company_name": "fox corporation"}}
            ]
        }
    }
    
    payload = {
        "query": query,
        "size": 15,
        "dataset": "resume"
    }

    try:
        resp = requests.post(url, json=payload, headers={'X-Api-Key': pdl_key}, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
        else:
            print(f"Error {resp.status_code}: {resp.text}")
            return
    except Exception as e:
        print(f"Exception: {e}")
        return

    results = []
    seen_names = set()
    
    for record in data.get('data', []):
        name = record.get('full_name')
        if not name or name.lower() in seen_names: continue
        
        fox_exp = [e for e in record.get('experience', []) if 'fox' in e.get('company', {}).get('name', '').lower()]
        if not fox_exp: continue
        
        fox_exp.sort(key=lambda x: x.get('end_date', '0000'), reverse=True)
        recent_fox = fox_exp[0]
        
        results.append({
            "name": name,
            "fox_role": recent_fox.get('title'),
            "tenure": f"{recent_fox.get('start_date')} to {recent_fox.get('end_date')}",
            "linkedin": f"linkedin.com/in/{record.get('linkedin_username')}" if record.get('linkedin_username') else "N/A"
        })
        seen_names.add(name.lower())

    print(json.dumps(results[:5], indent=2))

if __name__ == "__main__":
    get_fox_big_5_backup()
