import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

load_dotenv()

def diagnostic():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    cred_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
    sheet_id = os.getenv("SHEET_ID")
    
    print(f"--- Google Auth Diagnostic ---")
    print(f"Looking for credentials file: {cred_file}")
    
    if not os.path.exists(cred_file):
        print(f"ERROR: Credentials file '{cred_file}' NOT FOUND.")
        return

    try:
        creds = Credentials.from_service_account_file(cred_file, scopes=scopes)
        print(f"Service Account Email: {creds.service_account_email}")
        
        print(f"Attempting to authorize gspread...")
        gc = gspread.authorize(creds)
        print("gspread authorized.")
        
        if not sheet_id or "your_google_sheet_id" in sheet_id:
            print("ERROR: SHEET_ID in .env is missing or still set to placeholder.")
            return

        print(f"Attempting to open sheet: {sheet_id}")
        try:
            sheet = gc.open_by_key(sheet_id)
            print(f"SUCCESS: Opened sheet '{sheet.title}'")
            
            print("Attempting to list worksheets...")
            ws_list = [ws.title for ws in sheet.worksheets()]
            print(f"Worksheets found: {ws_list}")
            
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"ERROR: Spreadsheet with ID '{sheet_id}' NOT FOUND.")
            print(f"IMPORTANT: Ensure the sheet is shared with {creds.service_account_email}")
        except gspread.exceptions.APIError as e:
            print(f"ERROR: Google API Error: {e}")
            
    except Exception as e:
        print(f"FATAL ERROR during diagnostic: {e}")

if __name__ == "__main__":
    diagnostic()
