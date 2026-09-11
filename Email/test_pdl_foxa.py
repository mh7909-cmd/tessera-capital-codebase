#!/usr/bin/env python3
import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

def test_foxa_search():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(env_path)
    pdl_key = os.environ.get("PDL_API_KEY")
    
    # 1. Date Calculation (Same as production)
    six_months_ago = "2025-10-22" # Today (April 2026) minus 6 months
    
    # 2. Refined PQL for Revenue/M&A/Strategy (Strictly NO Engineers)
    # We target 'Strategy', 'M&A', 'Revenue', 'Sales', 'Finance'
    # We exclude 'Engineering', 'Developer', 'Software'
    
    company = "Fox Corporation"
    keywords = ["Strategy", "M&A", "Revenue", "Sales", "Finance", "Partnerships", "Corporate Development"]
    keyword_query = " OR ".join([f'job_title:"{kw}"' for kw in keywords])
    
    # Exclude technical roles to ensure relevance to 'Controversy' and 'Merger'
    exclude_query = 'NOT job_title:("Engineer", "Developer", "Software", "Technical", "Data Scientist")'
    
    pql = f"""
    work_history_company_name:"{company}" 
    AND NOT job_company_name:"{company}" 
    AND work_history_end_date:[* TO {six_months_ago}]
    AND ({keyword_query})
    AND {exclude_query}
    AND work_email:exists
    """.strip().replace('\n', ' ')

    print(f"\n🔍 [TESTING] Target Company: {company}")
    print(f"📊 [OBJECTIVE] Analyze Revenue Impact & Merger Risk")
    print(f"🛡️ [COMPLIANCE] Departure date BEFORE {six_months_ago}")
    print(f"🎯 [PQL] {pql}\n")

    url = "https://api.peopledatalabs.com/v5/person/search"
    params = {
        'api_key': pdl_key,
        'query': pql,
        'size': 5, # Show top 5 for the user to pick from
        'dataset': 'identity'
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for record in data.get('data', []):
                # Find the 'Fox' experience to show the user the tenure
                fox_exp = [exp for exp in record.get('experience', []) if 'fox' in exp.get('company', {}).get('name', '').lower()]
                tenure = "Unknown"
                if fox_exp:
                    start = fox_exp[0].get('start_date', 'N/A')
                    end = fox_exp[0].get('end_date', 'N/A')
                    tenure = f"{start} to {end}"

                results.append({
                    'Name': record.get('full_name'),
                    'Role': record.get('job_title'),
                    'Tenure_at_Fox': tenure,
                    'LinkedIn': f"linkedin.com/in/{record.get('linkedin_username')}" if record.get('linkedin_username') else "N/A"
                })
            
            print(json.dumps(results, indent=2))
        else:
            print(f"❌ PDL Error: {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_foxa_search()
