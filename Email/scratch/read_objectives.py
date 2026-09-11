#!/usr/bin/env python3
import gspread
import os
import json
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

def get_objectives():
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_file = '/Users/mayankhinduja/Desktop/Demo/Email/service_account.json'
    
    try:
        creds = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key('1HN7Fm3zoK6EsuGmzaLd4Hrj_fKJYMbZsCrmMJcrjRr8')
        
        tickers = ['FOXA', 'DAL', 'XYL', 'TTWO', 'ALGN']
        results = []
        
        for t in tickers:
            try:
                ws = spreadsheet.worksheet(t)
                headers = ws.row_values(1)
                first_row = ws.row_values(2)
                
                objective = "Diligence needed"
                if 'ai_summary' in headers:
                    objective = first_row[headers.index('ai_summary')]
                elif 'reason' in headers:
                    objective = first_row[headers.index('reason')]
                
                results.append({"ticker": t, "objective": objective})
            except Exception as e:
                # print(f"Error reading {t}: {e}")
                pass
                
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        print(f"Auth Error: {e}")

if __name__ == "__main__":
    get_objectives()
