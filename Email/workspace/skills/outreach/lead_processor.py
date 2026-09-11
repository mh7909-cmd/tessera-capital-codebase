#!/usr/bin/env python3
import gspread
import os
import sys
import json
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load env from root directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env'))

PIPELINE_SHEET_ID = "1sH3zh2R2eUWsGFZr4oLe6hV5W47ulr_5JJzhFydcjTM"

def _get_client():
    creds_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    if not os.path.exists(creds_file):
        root_creds_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), creds_file)
        if os.path.exists(root_creds_file):
            creds_file = root_creds_file
        else:
            return None
            
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    return gspread.authorize(creds)

def ensure_ticker_tab(spreadsheet, ticker):
    """Ensures a ticker tab exists and has the correct headers."""
    headers = ["Name", "Email", "Role", "LinkedIn", "Company", "Status", "Topic"]
    try:
        worksheet = spreadsheet.worksheet(ticker)
    except gspread.exceptions.WorksheetNotFound:
        print(f"   [PROVISIONING] Creating missing tab for {ticker}...")
        worksheet = spreadsheet.add_worksheet(title=ticker, rows="100", cols="20")
    
    # Check headers
    try:
        first_row = worksheet.row_values(1)
        if not first_row or "Name" not in first_row:
            print(f"   [PROVISIONING] Initializing headers for {ticker}...")
            worksheet.update('A1:G1', [headers])
    except Exception as e:
        print(f"   [PROVISIONING] Header error for {ticker}: {e}")
    return worksheet.id

def find_pending_tickers():
    client = _get_client()
    if not client:
        print("Error: Could not authorize Google Sheets client.")
        return []
    
    try:
        spreadsheet = client.open_by_key(PIPELINE_SHEET_ID)
        queue_worksheet = spreadsheet.worksheet("Pipeline Queue")
        records = queue_worksheet.get_all_records()
        
        pending = []
        for i, row in enumerate(records):
            # Normalize keys to handle 'Status' vs 'status' and 'Ticker' vs 'ticker'
            normalized_row = {k.lower(): v for k, v in row.items()}
            
            if normalized_row.get('status', '').lower() == 'pending':
                ticker = normalized_row.get('ticker')
                if ticker:
                    # Auto-provision tab when detected as pending
                    ensure_ticker_tab(spreadsheet, ticker)
                
                # Store the absolute row index (1-indexed, +1 for header)
                row['row_index'] = i + 2
                pending.append(row)
        return pending
    except Exception as e:
        print(f"Error fetching pending tickers: {e}")
        return []

def get_leads_from_ticker(ticker):
    client = _get_client()
    if not client:
        return []
    
    try:
        spreadsheet = client.open_by_key(PIPELINE_SHEET_ID)
        ensure_ticker_tab(spreadsheet, ticker)
        worksheet = spreadsheet.worksheet(ticker)
                
        records = worksheet.get_all_records()
        leads = []
        for i, row in enumerate(records):
            # Try various column names for status
            status_keys = [k for k in row.keys() if 'status' in k.lower()]
            status = row.get(status_keys[0], '') if status_keys else ''
            
            if status.lower() not in ['sent', 'done', 'skipped']:
                row['row_index'] = i + 2
                row['ticker_tab'] = ticker
                leads.append(row)
        return leads
    except Exception as e:
        print(f"Error fetching leads for {ticker}: {e}")
        return []

def mark_ticker_done(row_index):
    client = _get_client()
    if not client:
        return
    try:
        spreadsheet = client.open_by_key(PIPELINE_SHEET_ID)
        queue_worksheet = spreadsheet.worksheet("Pipeline Queue")
        # Column 6 is 'status' based on ['ticker', 'company', 'position lean', 'diligence aspect', 'rationale', 'status']
        queue_worksheet.update_cell(row_index, 6, 'done')
    except Exception as e:
        print(f"Error updating ticker status: {e}")

def mark_lead_sent(ticker, row_index):
    client = _get_client()
    if not client:
        return
    try:
        spreadsheet = client.open_by_key(PIPELINE_SHEET_ID)
        worksheet = spreadsheet.worksheet(ticker)
        # We need to find the 'status' column index inside the ticker tab
        headers = worksheet.row_values(1)
        status_col = -1
        for i, h in enumerate(headers):
            if 'status' in h.lower():
                status_col = i + 1
                break
        
        if status_col != -1:
            worksheet.update_cell(row_index, status_col, 'sent')
        else:
            # If no status column, maybe append it? For now just log
            print(f"Warning: No 'status' column found in {ticker} tab.")
    except Exception as e:
        print(f"Error updating lead status in {ticker}: {e}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        pending = find_pending_tickers()
        if not pending:
            print("No pending tickers found.")
            return
            
        all_leads = []
        import time
        max_leads = 5
        
        for t in pending:
            if len(all_leads) >= max_leads:
                break
                
            leads = get_leads_from_ticker(t['ticker'])
            time.sleep(1.1) # Respect 60 requests per minute limit
            
            for l in leads:
                # Merge ticker info
                l['ticker_reason'] = t.get('reason', '')
                l['ticker_company'] = t.get('company', '')
                l['ticker_row_index'] = t['row_index']
                all_leads.append(l)
                if len(all_leads) >= max_leads:
                    break
        
        print(json.dumps(all_leads, indent=2))
        
    elif len(sys.argv) > 3 and sys.argv[1] == "--mark-done":
        ticker = sys.argv[2]
        ticker_row = int(sys.argv[3])
        lead_row = int(sys.argv[4]) if len(sys.argv) > 4 else None
        
        mark_ticker_done(ticker_row)
        if lead_row:
            mark_lead_sent(ticker, lead_row)
        print(f"Marked {ticker} outreach as done.")

if __name__ == "__main__":
    main()
