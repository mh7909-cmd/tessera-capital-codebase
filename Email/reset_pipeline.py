import gspread, os
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

def reset_pipeline():
    load_dotenv()
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_file = '/Users/mayankhinduja/Desktop/Demo/Email/service_account.json'
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    
    pipeline_id = '1sH3zh2R2eUWsGFZr4oLe6hV5W47ulr_5JJzhFydcjTM'
    spreadsheet = client.open_by_key(pipeline_id)
    queue = spreadsheet.worksheet('Pipeline Queue')
    
    # Reset FLY status to pending
    cells = queue.findall('FLY')
    for cell in cells:
        queue.update_cell(cell.row, 5, 'pending')
    print("✅ FLY status reset to pending.")
    
    # Also reset the FLY expert status
    try:
        fly_tab = spreadsheet.worksheet('FLY')
        fly_tab.update_cell(2, 6, 'pending')
        print("✅ FLY Aviation Expert reset to pending.")
    except:
        pass

if __name__ == "__main__":
    reset_pipeline()
