#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

def get_mid_level_fox_diligence_5():
    # Use the working key
    pdl_key = 'a149de1cebe5b994f8305c7b782a2c427a3d0562ed412bed07d9fa5f8cdb8fbc'
    url = "https://api.peopledatalabs.com/v5/person/search"
    
    # MNPI Compliance Window: Jan 2023 - Oct 2025
    start_date = "2023-01-01"
    end_date = "2025-10-22"
    
    # Targeting mid-level roles that align with Fox Diligence Objectives (Ad Sales, Partnerships, Digital)
    query = {
        "bool": {
            "must": [
                {"match": {"experience.company.name": "Fox Corporation"}},
                {"range": {"experience.end_date": {"gte": start_date, "lte": end_date}}},
                {"bool": {
                    "should": [
                        {"match": {"experience.title": "Director Ad Sales"}},
                        {"match": {"experience.title": "Manager Strategic Partnerships"}},
                        {"match": {"experience.title": "Director Digital"}},
                        {"match": {"experience.title": "Manager Revenue"}},
                        {"match": {"experience.title": "Strategy Manager"}}
                    ]
                }}
            ],
            "must_not": [
                {"match": {"job_company_name": "Fox Corporation"}},
                {"term": {"experience.title": "vp"}},
                {"term": {"experience.title": "chief"}},
                {"term": {"experience.title": "executive"}}
            ]
        }
    }
    
    payload = {
        "query": query,
        "size": 20,
        "dataset": "resume"
    }

    try:
        resp = requests.post(url, json=payload, headers={'X-Api-Key': pdl_key}, timeout=20)
        data = resp.json()
    except Exception as e:
        print(f"Exception: {e}")
        return

    results = []
    seen_names = set()
    
    for record in data.get('data', []):
        name = record.get('full_name')
        if not name or name.lower() in seen_names: continue
        
        # Check current experience to ensure they've left
        exp_list = record.get('experience', [])
        fox_exp = [e for e in exp_list if 'fox' in e.get('company', {}).get('name', '').lower()]
        
        if not fox_exp: continue
        fox_exp.sort(key=lambda x: x.get('end_date', '0000'), reverse=True)
        recent_fox = fox_exp[0]
        
        results.append({
            "name": name,
            "historical_role": recent_fox.get('title'),
            "departure": recent_fox.get('end_date'),
            "linkedin": f"linkedin.com/in/{record.get('linkedin_username')}" if record.get('linkedin_username') else "N/A",
            "email": record.get('work_email') or (record.get('emails', [{}])[0].get('address') if record.get('emails') else "N/A")
        })
        seen_names.add(name.lower())

    print(json.dumps(results[:5], indent=2))

if __name__ == "__main__":
    get_mid_level_fox_diligence_5()
