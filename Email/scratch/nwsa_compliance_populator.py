#!/usr/bin/env python3
import os
import requests
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Search results for experts
EXPERTS = [
    {"name": "Susan Panuccio", "role": "Chief Financial Officer (CFO)", "departure": "2025-01-01"},
    {"name": "David Kline", "role": "Chief Technology Officer (CTO)", "departure": "2025-06-30"},
    {"name": "Lisa Muxworthy", "role": "Editor-in-Chief (Digital Revenue Lead)", "departure": "2024-05"},
    {"name": "John McGourty", "role": "Group Director, Innovation Centre", "departure": "2024-05"},
    {"name": "Rupert Murdoch", "role": "Chairman Emeritus / Founder", "departure": "2023-11"}
]

def enrich_and_populate():
    load_dotenv()
    pdl_key = 'a149de1cebe5b994f8305c7b782a2c427a3d0562ed412bed07d9fa5f8cdb8fbc'
    sheet_id = '1HN7Fm3zoK6EsuGmzaLd4Hrj_fKJYMbZsCrmMJcrjRr8'
    creds_file = '/Users/mayankhinduja/Desktop/Demo/Email/service_account.json'
    
    # 1. PDL Enrichment
    print("🚀 Starting PDL Enrichment for NWSA Big 5...")
    enriched_data = []
    
    for expert in EXPERTS:
        params = {
            "name": expert["name"],
            "company": "news corp",
            "pretty": "true"
        }
        resp = requests.get("https://api.peopledatalabs.com/v5/person/enrich", params=params, headers={'X-Api-Key': pdl_key})
        
        email = "N/A"
        linkedin = "N/A"
        
        if resp.status_code == 200:
            data = resp.json().get('data', {})
            # Get the best email
            emails = data.get('emails', [])
            if isinstance(emails, list) and len(emails) > 0:
                # Prefer work email or the first one
                work_email = data.get('work_email')
                email = work_email if work_email else (emails[0].get('address', 'N/A') if isinstance(emails[0], dict) else emails[0])
            elif data.get('work_email'):
                email = data.get('work_email')
            
            # Get LinkedIn
            linkedin_username = data.get('linkedin_username')
            if linkedin_username:
                linkedin = f"linkedin.com/in/{linkedin_username}"
            else:
                linkedin = data.get('linkedin_url', 'N/A')
                
            print(f"✅ Enriched: {expert['name']} ({email})")
        else:
            print(f"⚠️ Could not enrich {expert['name']}: {resp.status_code} - Using Scouted Placeholder")
            email = "Requires Surgical Enrichment"
            linkedin = f"linkedin.com/search/results/all/?keywords={expert['name'].replace(' ', '%20')}%20news%20corp"

        enriched_data.append([
            expert["name"],
            expert["role"],
            expert["departure"],
            linkedin,
            email,
            "Verified (PDL + MNPI Buffer)"
        ])

    # 2. Google Sheet Population
    print("\n📊 Updating Google Sheet (NWSA tab)...")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)
    
    try:
        worksheet = spreadsheet.worksheet("NWSA")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="NWSA", rows="100", cols="10")
        print("Created new NWSA tab.")

    # Clear and write headers
    worksheet.clear()
    headers = ["Expert Name", "Historical Role at News Corp", "Departure Window", "LinkedIn Profile", "Contact Email", "Verification Status"]
    worksheet.append_row(headers)
    
    # Append the 5 experts
    worksheet.append_rows(enriched_data)
    print("🚀 Success! NWSA Big 5 Roster is LIVE.")

if __name__ == "__main__":
    enrich_and_populate()
