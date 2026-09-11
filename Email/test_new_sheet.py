import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    creds_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    target = os.environ.get("GOOGLE_SHEET_NAME", "Email Thread")
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    try:
        creds = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(creds)
        
        print(f"Attempting to open: {target}")
        spreadsheet = client.open(target)
        print(f"SUCCESS: Successfully opened '{target}'")
        
        worksheet = spreadsheet.get_worksheet(0)
        print(f"Worksheet 0 title: {worksheet.title}")
        
    except Exception as e:
        print(f"FAILURE: {e}")
        try:
            client = gspread.authorize(creds)
            print("Listing all accessible spreadsheets:")
            for s in client.openall():
                print(f" - {s.title}")
        except:
            pass

if __name__ == "__main__":
    main()
