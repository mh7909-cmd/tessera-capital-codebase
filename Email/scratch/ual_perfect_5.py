#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

def get_ual_perfect_5():
    # Use the new working key
    pdl_key = 'a149de1cebe5b994f8305c7b782a2c427a3d0562ed412bed07d9fa5f8cdb8fbc'
    url = "https://api.peopledatalabs.com/v5/person/search"
    
    # Oct 2025 cutoff
    compliance_cutoff = "2025-10-22"
    
    # Hybrid Search for UAL: Looking for Operations, Finance, Revenue, and Strategy leaders.
    query = {
        "bool": {
            "must": [
                {"bool": {
                    "should": [
                        {"term": {"experience.company.name": "united airlines"}},
                        {"term": {"experience.company.website": "united.com"}},
                        {"term": {"experience.company.id": "jU85MnC6WX7ISormfWX0XQM2Aijb"}}
                    ]
                }},
                {"range": {"experience.end_date": {"gte": "2023-01-01", "lte": compliance_cutoff}}},
                {"bool": {
                    "should": [
                        {"term": {"experience.title": "strategy"}},
                        {"term": {"experience.title": "finance"}},
                        {"term": {"experience.title": "operations"}},
                        {"term": {"experience.title": "revenue"}},
                        {"term": {"experience.title": "director"}},
                        {"term": {"experience.title": "vp"}},
                        {"term": {"experience.title": "vice president"}},
                        {"term": {"experience.title": "managing director"}}
                    ]
                }}
            ],
            "must_not": [
                {"term": {"job_company_name": "united airlines"}},
                {"term": {"job_company_website": "united.com"}},
                {"term": {"job_title": "pilot"}},
                {"term": {"job_title": "flight attendant"}},
                {"term": {"job_title": "engineer"}},
                {"term": {"job_title": "intern"}}
            ]
        }
    }
    
    payload = {
        "query": query,
        "size": 50,
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
    
    # Priority keywords for matching 'Proper Primary Diligence'
    priority_keywords = ['strategy', 'finance', 'revenue', 'network planning', 'commercial', 'managing director', 'vp']
    
    for record in data.get('data', []):
        name = record.get('full_name')
        if not name or name.lower() in seen_names: continue
        
        ual_exp = [e for e in record.get('experience', []) if 'united' in e.get('company', {}).get('name', '').lower() or e.get('company', {}).get('website') == 'united.com']
        if not ual_exp: continue
        
        ual_exp.sort(key=lambda x: x.get('end_date', '0000'), reverse=True)
        recent_ual = ual_exp[0]
        
        title = recent_ual.get('title', '').lower()
        
        # Scoring based on seniority and relevance
        score = 0
        if any(kw in title for kw in priority_keywords): score += 10
        if 'managing director' in title: score += 15
        if 'vice president' in title or 'vp' in title: score += 20
        if 'director' in title: score += 5
        
        results.append({
            "name": name,
            "role": recent_ual.get('title'),
            "tenure": f"{recent_ual.get('start_date')} to {recent_ual.get('end_date')}",
            "linkedin": f"linkedin.com/in/{record.get('linkedin_username')}" if record.get('linkedin_username') else "N/A",
            "score": score
        })
        seen_names.add(name.lower())

    results.sort(key=lambda x: x['score'], reverse=True)
    print(json.dumps(results[:10], indent=2))

if __name__ == "__main__":
    get_ual_perfect_5()
