import gspread, os
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load env from root directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def reset_leads():
    creds_file = 'Email/service_account.json'
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    
    spreadsheet = client.open_by_key('1sH3zh2R2eUWsGFZr4oLe6hV5W47ulr_5JJzhFydcjTM')
    
    # Reset Pipeline Queue
    queue = spreadsheet.worksheet('Pipeline Queue')
    cell = queue.find('DAL')
    queue.update_cell(cell.row, 5, 'pending')
    print("Pipeline Queue: DAL set to pending.")
    
    # Reset DAL tab
    dal = spreadsheet.worksheet('DAL')
    data = dal.get_all_values()
    headers = data[0]
    status_idx = headers.index('Status') + 1
    
    for i in range(2, len(data) + 1):
        dal.update_cell(i, status_idx, 'pending')
    
    print(f"DAL Tab: {len(data)-1} leads set to pending.")

if __name__ == "__main__":
    reset_leads()
