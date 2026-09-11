import json
import os
import threading
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime

# Load env from root directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env'))

# Import premium utility from root Codebase
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 'Codebase'))
from sheets_utils import DiligenceSheetsUtils

STATE_FILE = os.path.join(os.path.dirname(__file__), 'campaign_state.json')

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"threads": {}}
    with open(STATE_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"threads": {}}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def _get_creds_and_client():
    creds_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    if not os.path.exists(creds_file):
        root_creds_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), creds_file)
        if os.path.exists(root_creds_file):
            creds_file = root_creds_file
        else:
            return None, None
            
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    return creds, client

def _format_history(history):
    """Converts the history list into a readable string with timestamps."""
    formatted = []
    for msg in history:
        role = msg.get("role", "unknown").capitalize()
        # Convert user to User and assistant to Assistant for clarity
        if role == "Assistant":
            pass
        elif role == "User":
            pass
        else:
            role = "Agent"
        
        timestamp = msg.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        content = msg.get("content", "")
        formatted.append(f"[{timestamp}] {role}: {content}")
    return "\n".join(formatted)

def _apply_formatting(worksheet, gc):
    """Applies premium institutional branding to the correspondence sheet."""
    try:
        utils = DiligenceSheetsUtils(gc)
        
        # 1. Apply Global Branding (Lexend font, row heights)
        utils._apply_global_formatting(worksheet)
        
        # 2. Custom Column Widths for Correspondence
        # Sender, Recipient Name, Email, Subject, Company, Initial Message-ID, Full_Thread_History, Research Topic
        col_widths = [140, 160, 220, 280, 160, 180, 600, 250]
        requests = []
        for i, width in enumerate(col_widths):
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": worksheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": i,
                        "endIndex": i + 1
                    },
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize"
                }
            })
        
        # 3. Header Formatting (Indigo)
        header_color = {"red": 0.1, "green": 0.1, "blue": 0.3} # Indigo
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 8
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": header_color,
                        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
            }
        })
        
        worksheet.spreadsheet.batch_update({"requests": requests})
    except Exception as e:
        print(f"Warning: Failed to apply premium formatting: {e}")


def _sync_to_sheets(name, email, subject, company, message_id, history, topic, ticker=None):
    """Appends a new outreach record to the Google Sheet with initial history."""
    creds, client = _get_creds_and_client()
    if not client:
        print("Warning: Google Service Account file not found. Skipping Google Sheets sync.")
        return

    try:
        sheet_id = os.environ.get("THREAD_SHEET_ID") or os.environ.get("GOOGLE_SHEET_ID")
        sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Email Thread")
        
        if sheet_id:
            spreadsheet = client.open_by_key(sheet_id)
        else:
            spreadsheet = client.open(sheet_name)
            
        # Select worksheet by ticker name, create if it doesn't exist
        ticker_name = ticker if ticker else "General"
        try:
            worksheet = spreadsheet.worksheet(ticker_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=ticker_name, rows="100", cols="10")
            print(f"Created new worksheet for ticker: {ticker_name}")

        # Check for header and ensure Initial Message-ID is present
        try:
            headers = worksheet.row_values(1)
        except:
            headers = []
            
        if not headers or "Initial Message-ID" not in headers:
            worksheet.insert_row(["Sender", "Recipient Name", "Email", "Subject", "Company", "Initial Message-ID", "Full_Thread_History", "Research Topic"], 1)
        
        # Format the initial history
        history_text = _format_history(history)

        # Append row: Sender, Name, Email, Subject, Company, Message-ID, History, Topic
        sender_name = "Mayank Hinduja"
        worksheet.append_row([sender_name, name, email, subject, company, message_id, history_text, topic])
        
        # Apply formatting
        _apply_formatting(worksheet, client)
        
        # print(f"Successfully synced outreach for {email} to Google Sheets.")
    except Exception as e:
        print(f"Failed to sync outreach to Google Sheets: {e}")

def _update_thread_history_in_sheets(initial_id, history):
    """Updates the Full_Thread_History cell for an existing outreach record."""
    creds, client = _get_creds_and_client()
    if not client:
        return

    try:
        # Get thread details to find the ticker
        thread_details = get_thread_by_id(initial_id)
        ticker = thread_details.get("ticker", "General") if thread_details else "General"

        sheet_id = os.environ.get("THREAD_SHEET_ID") or os.environ.get("GOOGLE_SHEET_ID")
        sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Email Thread")
        
        if sheet_id:
            spreadsheet = client.open_by_key(sheet_id)
        else:
            spreadsheet = client.open(sheet_name)
            
        worksheet = spreadsheet.worksheet(ticker)

        # Find the cell matching the initial_id in Column F (6th column)
        cell = worksheet.find(initial_id, in_column=6)
        if cell:
            # Update the cell in Column G (7th column) of the same row
            history_text = _format_history(history)
            worksheet.update_cell(cell.row, 7, history_text)
            # print(f"Successfully updated thread history for {initial_id} in Google Sheets.")
    except Exception as e:
        print(f"Failed to update thread history in Google Sheets: {e}")

def record_outreach(message_id, to_email, subject, name, company, body, ticker=None, topic="General Market Research"):
    state = load_state()
    # Strip angle brackets if present
    clean_id = message_id.strip('<>')
    
    thread_data = {
        "to_email": to_email,
        "subject": subject,
        "name": name,
        "company": company,
        "ticker": ticker,
        "topic": topic,
        "initial_id": clean_id,
        "history": [
            {
                "role": "assistant", 
                "content": body,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ],
        "status": "waiting" # waiting for reply
    }
    
    state["threads"][clean_id] = thread_data
    save_state(state)
    
    # Sync to Google Sheets in background
    threading.Thread(
        target=_sync_to_sheets, 
        args=(name, to_email, subject, company, clean_id, thread_data["history"], topic, ticker),
        daemon=False
    ).start()

def get_thread_by_id(message_id):
    clean_id = message_id.strip('<>')
    state = load_state()
    return state["threads"].get(clean_id)

def add_message_to_thread(thread_id, role, content, new_message_id=None):
    clean_id = thread_id.strip('<>')
    state = load_state()
    if clean_id in state["threads"]:
        # Add to history with timestamp
        state["threads"][clean_id]["history"].append({
            "role": role, 
            "content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Get the initial ID to identify the row in the sheet
        initial_id = state["threads"][clean_id].get("initial_id", clean_id)
        
        # If there's a new message ID (e.g. user reply ID or assistant reply ID),
        # link it to this same thread dict so future replies to IT will be caught.
        if new_message_id:
            clean_new_id = new_message_id.strip('<>')
            state["threads"][clean_new_id] = state["threads"][clean_id]
            
        save_state(state)
        
        # Update thread history in Google Sheets in background
        threading.Thread(
            target=_update_thread_history_in_sheets,
            args=(initial_id, state["threads"][clean_id]["history"]),
            daemon=True
        ).start()

