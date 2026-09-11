import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

load_dotenv()

def inspect_sheet():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)
    source_id = os.getenv('SOURCE_SHEET_ID')
    
    sheet = client.open_by_key(source_id)
    print(f"Inspecting Sheet: {sheet.title}")
    
    for worksheet in sheet.worksheets():
        print(f"\nTab: {worksheet.title}")
        try:
            headers = worksheet.row_values(1)
            print(f"Headers: {headers}")
        except Exception as e:
            print(f"Could not read headers: {e}")

if __name__ == "__main__":
    inspect_sheet()
