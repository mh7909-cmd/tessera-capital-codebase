import gspread, os
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

def rank_tickers():
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
        import time
        time.sleep(1.5) # Avoid 429 quota exceeded
        title = ws.title
        if title in ['Dashboard', 'Sheet5']:
            continue
            
        data = ws.get_all_values()
        if len(data) < 2:
            continue
            
        headers = data[0]
        row = data[1]
        
        try:
            composite_idx = headers.index('composite_score')
            upside_idx = headers.index('dcf_upside')
            
            composite_score = float(row[composite_idx]) if row[composite_idx] else 0
            upside = float(row[upside_idx]) if row[upside_idx] else 0
            
            results.append({
                'ticker': title,
                'composite': composite_score,
                'upside': upside
            })
        except:
            continue
            
    # Sort by composite score (Primary) and upside (Secondary)
    results.sort(key=lambda x: (x['composite'], x['upside']), reverse=True)
    
    for r in results[:10]:
        print(f"Ticker: {r['ticker']}, Composite: {r['composite']:.2f}, Upside: {r['upside']:.2%}")

if __name__ == "__main__":
    rank_tickers()
