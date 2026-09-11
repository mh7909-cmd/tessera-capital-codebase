import os
import sys
import time
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Add required paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(ROOT_DIR, 'Email'))
sys.path.append(os.path.join(ROOT_DIR, 'Email', 'workspace', 'skills', 'outreach'))

from send_email import send_personalized_email

load_dotenv()

def apply_row_formatting(leads_ws, row_idx: int, is_sent: bool = False):
    """Apply institutional-grade formatting to a specific data row (Kinetic Mode)."""
    try:
        sheet_id = int(leads_ws.id)
        requests = []
        
        # 1. Row background (Striping)
        bg = {"red": 0.96, "green": 0.97, "blue": 0.98} if (row_idx % 2 == 1) else {"red": 0.93, "green": 0.94, "blue": 0.96}
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 0, "endColumnIndex": 5},
                "cell": {"userEnteredFormat": {"backgroundColor": bg}},
                "fields": "userEnteredFormat.backgroundColor"
            }
        })
        
        # 2. Status badge
        status_bg = {"red": 0.88, "green": 0.96, "blue": 0.88} if is_sent else {"red": 1.00, "green": 0.97, "blue": 0.88}
        status_fg = {"red": 0.10, "green": 0.45, "blue": 0.15} if is_sent else {"red": 0.55, "green": 0.35, "blue": 0.00}
        
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 5, "endColumnIndex": 6},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": status_bg,
                    "textFormat": {"fontFamily": "Lexend", "fontSize": 10, "bold": True, "foregroundColor": status_fg},
                    "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
                }},
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
            }
        })
        
        leads_ws.spreadsheet.batch_update({"requests": requests})
    except:
        pass

def run_direct_outreach():
    print("\n📩 [SHADOW_MODE] Initiating Direct Expert Outreach for FLY...")
    
    # Target delivery address for ALL demo inquiries
    DEMO_INBOX = "mayank.hinduja27@gmail.com"

    # Expert roster sourced from pipeline sheet — all routed to demo inbox
    experts = [
        {"Name": "Shubhanker Kapoor", "Company": "Impulse Space", "Role": "Lead, Propulsion Systems", "DisplayEmail": "mayank.hinduja27@gmail.com", "Topic": "Propulsion Systems"},
        {"Name": "Khaled Moharam", "Company": "PulseForge, Inc.", "Role": "Lead Power Systems Engineer", "DisplayEmail": "mayank.hinduja27@gmail.com", "Topic": "Power Systems"},
        {"Name": "Isaac Browne", "Company": "Bechtel Corporation", "Role": "Launch Vehicle Systems Engineer", "DisplayEmail": "mayank.hinduja27@gmail.com", "Topic": "Launch Systems"},
        {"Name": "Brandon Reemsnyder", "Company": "PLD Space", "Role": "Propulsion Engineer II", "DisplayEmail": "mayank.hinduja27@gmail.com", "Topic": "Propulsion Design"},
        {"Name": "Kyle Hillman", "Company": "SpaceX", "Role": "Propulsion Engineer", "DisplayEmail": "mayank.hinduja27@gmail.com", "Topic": "Launch Engineering"},
        {"Name": "Jacob Frogget", "Company": "Cadence Design Systems", "Role": "Senior FPGA Engineer", "DisplayEmail": "mayank.hinduja27@gmail.com", "Topic": "Avionics Hardware"},
    ]

    # Setup GSheets connection for live status updates
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        gc = gspread.authorize(creds)
        pipe_sh = gc.open_by_key(os.getenv('PIPELINE_SHEET_ID'))
        leads_ws = pipe_sh.worksheet('Leads')
    except Exception as e:
        print(f"   ⚠️ [SYNC_ERROR] Could not connect to Google Sheets: {e}")
        leads_ws = None

    for i, lead in enumerate(experts):
        row_idx = i + 1 # 1-based, header is row 1
        try:
            print(f"   [DISPATCH] Generating institutional inquiry for {lead['Name']}...")
            
            # SMTP delivery to Mayank for ALL experts to show the "send" works
            success = send_personalized_email(
                to_email=DEMO_INBOX,
                lead_name=lead['Name'],
                company_name=lead['Company'],
                role=lead['Role'],
                ticker="FLY",
                research_reason=lead['Topic'],
                copy_me=True
            )
            
            if success:
                print(f"   ✅ [SENT] Inquiry delivered → Expert Node Sync: ACTIVE")
                print(f"   🎯 [SHADOW_MODE] Delivery confirmed via secure SMTP bridge.")
                
                # Update GSheets status to 'sent' (Green) LIVE
                if leads_ws:
                    leads_ws.update_acell(f"F{row_idx+1}", "sent")
                    apply_row_formatting(leads_ws, row_idx, is_sent=True)
                
                # THEATRICAL PACING: Stay on Leads tab to show the status change
                time.sleep(4)
            else:
                print(f"   ⚠️ [ERROR] Delivery failure for {lead['Name']}.")
                time.sleep(1)

        except Exception as e:
            print(f"   ⚠️ [OUTREACH_ERROR] {lead['Name']}: {e}")

    # AFTER ALL 6 EMAILS ARE SENT: Update Pipeline Queue status for FLY from 'pending' to 'done'
    if leads_ws:
        try:
            queue_ws = pipe_sh.worksheet("Pipeline Queue")
            q_tickers = [str(t).strip().upper() for t in queue_ws.col_values(1)]
            if "FLY" in q_tickers:
                f_idx = q_tickers.index("FLY") + 1
                queue_ws.update_cell(f_idx, 6, "done")
                print(f"   ✅ [SYNC] Pipeline status for FLY updated to DONE.")
            else:
                print(f"   ⚠️ [SYNC_WARN] 'FLY' ticker not found in Pipeline Queue. Skipping final status promotion.")
        except Exception as e:
            print(f"   ⚠️ [SYNC_ERROR] Could not finalize pipeline queue status: {e}")

if __name__ == "__main__":
    run_direct_outreach()
