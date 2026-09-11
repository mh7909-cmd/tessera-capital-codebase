import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

load_dotenv()

def check_sheet_data(ticker):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    MASTER_SHEET_ID = os.getenv("MASTER_SHEET_ID")
    
    cred_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
    if not os.path.exists(cred_file):
        cred_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')

    creds = Credentials.from_service_account_file(cred_file, scopes=SCOPES)
    gc = gspread.authorize(creds)
    
    sheet = gc.open_by_key(MASTER_SHEET_ID)
    try:
        ws = sheet.worksheet(ticker)
        data = ws.get_all_records()
        print(f"📊 Data for {ticker}:")
        for row in data:
            print(f"  EC 1: {str(row.get('EC 1 Summary'))[:50]}...")
            print(f"  EC 2: {str(row.get('EC 2 Summary'))[:50]}...")
            print(f"  Overall Sentiment: {row.get('Overall Sentiment')}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_sheet_data("FLY")
