#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

def get_fox_big_5():
    load_dotenv('/Users/mayankhinduja/Desktop/Demo/.env')
    pdl_key = os.environ.get("PDL_API_KEY")
    fallback_key = os.environ.get("PDL_API_KEY_FALLBACK")
    
    url = "https://api.peopledatalabs.com/v5/person/search"
    
    # Oct 2025 (6 month buffer)
    compliance_cutoff = "2025-10-22"
    
    # Broad query for Fox Strategy/Finance/Revenue using both name and website
    query = {
        "bool": {
            "must": [
                {"bool": {
                    "should": [
                        {"term": {"experience.company.name": "fox corporation"}},
                        {"term": {"experience.company.name": "fox news"}},
                        {"term": {"experience.company.website": "fox.com"}},
                        {"term": {"experience.company.website": "foxcorporation.com"}}
                    ]
                }},
                {"range": {"experience.end_date": {"gte": "2022-01-01", "lte": compliance_cutoff}}},
                {"exists": {"field": "work_email"}},
                {"bool": {
                    "should": [
                        {"term": {"experience.title": "strategy"}},
                        {"term": {"experience.title": "finance"}},
                        {"term": {"experience.title": "revenue"}},
                        {"term": {"experience.title": "advertising"}},
                        {"term": {"experience.title": "sales"}},
                        {"term": {"experience.title": "corporate development"}},
                        {"term": {"experience.title": "product"}},
                        {"term": {"experience.title": "director"}},
                        {"term": {"experience.title": "manager"}},
                        {"term": {"experience.title": "vp"}}
                    ]
                }}
            ],
            "must_not": [
                {"term": {"job_company_name": "fox corporation"}},
                {"term": {"job_title": "engineer"}},
                {"term": {"job_title": "developer"}},
                {"term": {"job_title": "intern"}},
                {"term": {"job_title": "assistant"}}
            ]
        }
    }
    
    payload = {
        "query": query,
        "size": 100,
        "dataset": "resume"
    }

    keys = [pdl_key, fallback_key]
    data = None
    for k in keys:
        if not k: continue
        try:
            print(f"Trying key starting with {k[:5]}...")
            resp = requests.post(url, json=payload, headers={'X-Api-Key': k}, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                break
            else:
                print(f"Key error ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"Exception: {e}")
            continue
            
    if not data:
        print("❌ Search failed.")
        return

    results = []
    seen_names = set()
    
    # Priority keywords for filtering the 100 results
    priority_keywords = ['strategy', 'revenue', 'finance', 'corporate development', 'm&a', 'advertising sales']
    
    for record in data.get('data', []):
        name = record.get('full_name')
        if not name or name.lower() in seen_names: continue
        
        fox_exp = [e for e in record.get('experience', []) if 'fox' in e.get('company', {}).get('name', '').lower()]
        if not fox_exp: continue
        
        fox_exp.sort(key=lambda x: x.get('end_date', '0000'), reverse=True)
        recent_fox = fox_exp[0]
        
        # Determine seniority/relevance score
        title = recent_fox.get('title', '').lower()
        score = 0
        if any(kw in title for kw in priority_keywords): score += 10
        if 'director' in title: score += 5
        if 'vp' in title or 'vice president' in title: score += 10
        if 'senior' in title or 'sr' in title: score += 2
        
        results.append({
            "name": name,
            "fox_role": recent_fox.get('title'),
            "tenure": f"{recent_fox.get('start_date')} to {recent_fox.get('end_date')}",
            "linkedin": f"linkedin.com/in/{record.get('linkedin_username')}" if record.get('linkedin_username') else "N/A",
            "score": score
        })
        seen_names.add(name.lower())

    # Sort by relevance score
    results.sort(key=lambda x: x['score'], reverse=True)

    print(json.dumps(results[:15], indent=2))

if __name__ == "__main__":
    get_fox_big_5()
