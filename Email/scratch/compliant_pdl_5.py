#!/usr/bin/env python3
import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

def get_compliant_big_5():
    # Use the working key provided by the user
    pdl_key = 'a149de1cebe5b994f8305c7b782a2c427a3d0562ed412bed07d9fa5f8cdb8fbc'
    url = "https://api.peopledatalabs.com/v5/person/search"
    
    # MNPI Compliance Window: Departed between Jan 2023 and Oct 2025.
    # This ensures a >6 month buffer from the current date (April 2026).
    start_date = "2023-01-01"
    end_date = "2025-10-22"
    
    print(f"🚀 Executing MNPI-Compliant Search (Window: {start_date} to {end_date})")
    
    # Simplest possible search to avoid 404s - filtering in Python
    query = {
        "bool": {
            "must": [
                {"match": {"experience.company.name": "Delta Air Lines"}},
                {"range": {"experience.end_date": {"gte": start_date, "lte": end_date}}}
            ],
            "must_not": [
                {"match": {"job_company_name": "Delta Air Lines"}}
            ]
        }
    }
    
    payload = {
        "query": query,
        "size": 100,
        "dataset": "resume"
    }

    try:
        resp = requests.post(url, json=payload, headers={'X-Api-Key': pdl_key}, timeout=20)
        if resp.status_code != 200:
            print(f"Error {resp.status_code}: {resp.text}")
            return
        data = resp.json()
    except Exception as e:
        print(f"Exception: {e}")
        return

    results = []
    seen_names = set()
    
    # Priority keywords for 'Proper' Seniority
    proper_titles = ['vice president', 'vp', 'director', 'managing director', 'lead', 'head']
    
    for record in data.get('data', []):
        name = record.get('full_name')
        if not name or name.lower() in seen_names: continue
        
        # Extract the historical role
        exp_list = record.get('experience', [])
        dal_exp = [e for e in exp_list if 'delta' in e.get('company', {}).get('name', '').lower()]
        
        if not dal_exp: continue
        
        # Sort by most recent departure
        dal_exp.sort(key=lambda x: x.get('end_date', '0000'), reverse=True)
        recent_dal = dal_exp[0]
        
        title = recent_dal.get('title', '').lower()
        dept_date = recent_dal.get('end_date', '')
        
        # Strict Date Check (PDL dates can be YYYY-MM or YYYY)
        if not dept_date or dept_date < "2023-01" or dept_date > "2025-10":
            continue
            
        # Proper Seniority Check
        if not any(kw in title for kw in proper_titles):
            continue

        results.append({
            "name": name,
            "historical_role": recent_dal.get('title'),
            "departure_date": dept_date,
            "company": "Delta Air Lines",
            "linkedin": f"linkedin.com/in/{record.get('linkedin_username')}" if record.get('linkedin_username') else "N/A",
            "emails": record.get('emails', []),
            "work_email": record.get('work_email', 'N/A')
        })
        seen_names.add(name.lower())

    # Present the top 5
    print("\n--- MNPI VERIFIED ROSTER (PDL SOURCE) ---")
    print(json.dumps(results[:5], indent=2))

if __name__ == "__main__":
    get_compliant_big_5()
