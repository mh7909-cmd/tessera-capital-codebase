#!/usr/bin/env python3
"""
Uploads the final Equity Screening Excel file to Google Sheets.
Appends the data as a new tab on the "Master Equity Screener" file.
"""

import sys
import os
import pandas as pd
from datetime import datetime
import time

try:
    import gspread
    from gspread_dataframe import set_with_dataframe
except ImportError:
    print("❌ gspread or gspread-dataframe not installed. Run: pip install gspread gspread-dataframe")
    sys.exit(1)

def upload_to_master_sheet(excel_file: str, creds_path: str = "client_secret.json", auth_user_path: str = "authorized_user.json", folder_id: str = "1B6shb7SZXVu6D-SPTyoUm9VJoFAkQmK3"):
    print("\n" + "="*80)
    print("STEP 3: GOOGLE SHEETS UPLOAD")
    print("="*80 + "\n")
    
    if not os.path.exists(creds_path) or not os.path.exists(auth_user_path):
        print(f"⚠️  Missing {creds_path} or {auth_user_path}. Skipping upload.")
        return False
        
    print(f"📡 Authenticating with Google Drive...")
    try:
        gc = gspread.oauth(
            credentials_filename=creds_path,
            authorized_user_filename=auth_user_path
        )
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

    # Get or create Master Sheet
    master_title = "Master Equity Screener"
    print(f"🔍 Looking for Google Sheet: '{master_title}'...")
    try:
        sh = gc.open(master_title)
        print(f"✅ Found existing Master Sheet: {sh.url}")
    except gspread.SpreadsheetNotFound:
        print(f"🆕 Creating new Master Sheet '{master_title}' in folder '{folder_id}'...")
        try:
            sh = gc.create(master_title, folder_id=folder_id)
            print(f"✅ Created Master Sheet: {sh.url}")
        except Exception as e:
            print(f"❌ Failed to create Master Sheet: {e}")
            return False

    # Determine unique tab name
    base_tab_name = datetime.now().strftime("%Y-%m-%d")
    tab_name = base_tab_name
    existing_tabs = [ws.title for ws in sh.worksheets()]
    
    counter = 1
    while tab_name in existing_tabs:
        counter += 1
        tab_name = f"{base_tab_name} Run {counter}"
        
    print(f"📑 Creating new tab: '{tab_name}'...")
    
    try:
        # Load the final Excel file, combining all sheets if necessary
        # However, earnings analyzer saves everything into "Earnings Analysis" sheet
        df = pd.read_excel(excel_file, sheet_name='Earnings Analysis')
    except Exception as e:
        print(f"❌ Failed to read {excel_file}: {e}")
        return False
        
    try:
        # Create worksheet (rows + 10 for padding, cols + 5)
        ws = sh.add_worksheet(title=tab_name, rows=len(df)+10, cols=len(df.columns)+5)
        
        # Upload data
        print("↗️  Uploading data to Google Sheets...")
        set_with_dataframe(ws, df)
        
        # Basic Formatting
        ws.format('A1:ZZ1', {
            "backgroundColor": {"red": 0.1, "green": 0.3, "blue": 0.4},
            "horizontalAlignment": "CENTER",
            "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True}
        })
        
        # If 'Sheet1' exists and is completely empty, it was auto-created. Delete it safely.
        if len(sh.worksheets()) > 1:
            for w in sh.worksheets():
                if w.title == 'Sheet1' and not w.get_all_values():
                    sh.del_worksheet(w)
                    
        print(f"✅ Successfully uploaded {len(df)} records to '{tab_name}'!")
        print(f"🔗 Link: {sh.url}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to upload data: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_to_sheets.py <final_excel_file>")
        sys.exit(1)
        
    excel_file = sys.argv[1]
    if not os.path.exists(excel_file):
        print(f"❌ File not found: {excel_file}")
        sys.exit(1)
        
    upload_to_master_sheet(excel_file)
