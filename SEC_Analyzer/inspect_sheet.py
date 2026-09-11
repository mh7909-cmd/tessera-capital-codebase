import gspread
from google.oauth2.service_account import Credentials
import os

def inspect_sheet():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds_path = 'credentials.json'
    if not os.path.exists(creds_path):
        print("Credentials file not found.")
        return
        
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)
    
    # User provided source sheet ID
    source_id = '1R7r1c_rO_-VAfmY_RsrwV1lrEE3q0LxPX-G4TNC4pME'
    
    try:
        sheet = client.open_by_key(source_id)
        print(f"Inspecting Sheet: {sheet.title}")
        
        for worksheet in sheet.worksheets():
            print(f"\nTab: {worksheet.title}")
            try:
                # Read first row to see headers
                headers = worksheet.row_values(1)
                print(f"Headers: {headers}")
                # Read first data row to see values
                first_row = worksheet.row_values(2)
                print(f"Sample Data: {first_row}")
            except Exception as e:
                print(f"Could not read content: {e}")
    except Exception as e:
        print(f"Error opening sheet: {e}")

if __name__ == "__main__":
    inspect_sheet()
