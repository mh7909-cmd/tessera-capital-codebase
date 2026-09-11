#!/usr/bin/env python3
import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

def test_pdl_json():
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    pdl_key = os.environ.get("PDL_API_KEY")
    
    url = "https://api.peopledatalabs.com/v5/person/search"
    
    # Simplified Elasticsearch Query
    query = {
        "bool": {
            "must": [
                {"term": {"experience.company.name": "fox corporation"}},
                {"exists": {"field": "work_email"}},
                {"range": {"experience.end_date": {"lte": "2025-10-22"}}}
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
        "size": 5,
        "dataset": "resume"
    }

    print(f"DEBUG: Sending Payload to PDL\n")

    # PDL expects the payload as a JSON string in the 'query' parameter for GET,
    # or as the body for POST. POST is cleaner.
    req_headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': pdl_key
    }
    
    try:
        resp = requests.post(url, json=payload, headers=req_headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Success! Found {data.get('total', 0)} total matches.")
            for record in data.get('data', []):
                print(f"- {record.get('full_name')} | {record.get('job_title')} | Left Fox: {record.get('experience', [{}])[0].get('end_date')}")
        else:
            print(f"❌ PDL Error ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_pdl_json()
