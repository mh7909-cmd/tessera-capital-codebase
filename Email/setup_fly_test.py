import gspread, os
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

def setup_fly_test():
    load_dotenv()
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_file = '/Users/mayankhinduja/Desktop/Demo/Email/service_account.json'
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    
    # 1. Pipeline Queue
    pipeline_id = '1sH3zh2R2eUWsGFZr4oLe6hV5W47ulr_5JJzhFydcjTM'
    ss_pipeline = client.open_by_key(pipeline_id)
    queue = ss_pipeline.worksheet('Pipeline Queue')
    queue.append_row([
        'FLY', 
        'Fly Leasing', 
        'Aviation', 
        'How are lease-rate factors and aircraft retirement cycles evolving in a high-rate environment?', 
        'pending'
    ])
    print("✅ Added 'FLY' to Pipeline Queue.")
    
    # 2. FLY Ticker Tab
    try:
        sheet = ss_pipeline.worksheet('FLY')
    except gspread.exceptions.WorksheetNotFound:
        sheet = ss_pipeline.add_worksheet('FLY', 100, 20)
        sheet.append_row(['Name', 'Email', 'Role', 'LinkedIn', 'Company', 'Status', 'Topic'])
        
    sheet.append_row([
        'Aviation Expert', 
        'mayank.hinduja27@gmail.com', 
        'Chief Fleet Strategist', 
        'https://linkedin.com/in/test', 
        'Fly Leasing', 
        'pending', 
        'Fleet Optimization'
    ])
    print("✅ Added 'Aviation Expert' lead to FLY tab.")

if __name__ == "__main__":
    setup_fly_test()
