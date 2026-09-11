import gspread, os
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

def analyze_sheet():
    load_dotenv()
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_file = '/Users/mayankhinduja/Desktop/Demo/Email/service_account.json'
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    
    sheet_id = '1HN7Fm3zoK6EsuGmzaLd4Hrj_fKJYMbZsCrmMJcrjRr8'
    spreadsheet = client.open_by_key(sheet_id)
    worksheets = spreadsheet.worksheets()
    
    results = []
    
    for ws in worksheets:
        title = ws.title
        if title in ['Dashboard', 'Sheet5']:
            continue
            
        data = ws.get_all_values()
        if len(data) < 2:
            continue
            
        # Try to find a score or summary
        row2 = data[1]
        results.append({
            'ticker': title,
            'data': row2
        })
        
    print(results)

if __name__ == "__main__":
    analyze_sheet()
