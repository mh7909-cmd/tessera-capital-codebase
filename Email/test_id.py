import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    creds_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    target_id = "1mBVNvsg6xnB4hV8Uc0YoAHX76gnrJTcBXmGNLe6bLZQ"
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    try:
        creds = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(creds)
        
        print(f"Attempting to open ID: {target_id}")
        spreadsheet = client.open_by_key(target_id)
        print(f"SUCCESS: Successfully opened '{spreadsheet.title}'")
        
        # Check columns
        worksheet = spreadsheet.get_worksheet(0)
        headers = worksheet.row_values(1)
        print(f"Current headers: {headers}")
        
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    main()
