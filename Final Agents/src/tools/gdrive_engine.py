import os
import io
import json
import gspread
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader
from docx import Document
from typing import List, Dict, Any

# Path to the service account credentials file
SERVICE_ACCOUNT_FILE = 'service_account.json'

def get_gdrive_service():
    """Build and return the Google Drive API service."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, 
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=creds)

def get_gsheets_client():
    """Build and return the Google Sheets API client."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly', 'https://www.googleapis.com/auth/drive.readonly']
    )
    return gspread.authorize(creds)

def list_files_in_folder(folder_id: str, sort_by_newest: bool = False) -> List[Dict[str, str]]:
    """List all files in a specific Google Drive folder, optionally sorted by newest first."""
    service = get_gdrive_service()
    query = f"'{folder_id}' in parents and trashed = false"
    orderby = "createdTime desc" if sort_by_newest else "name"
    results = service.files().list(q=query, fields="files(id, name, mimeType, createdTime)", orderBy=orderby).execute()
    return results.get('files', [])

def download_file_content(file_id: str, mime_type: str) -> bytes:
    """Download the content of a file from Google Drive."""
    service = get_gdrive_service()
    
    # Handle Google Docs formats by exporting them
    if mime_type == 'application/vnd.google-apps.document':
        request = service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    elif mime_type == 'application/vnd.google-apps.spreadsheet':
        request = service.files().export_media(fileId=file_id, mimeType='text/csv')
    else:
        request = service.files().get_media(fileId=file_id)
        
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return fh.getvalue()

def parse_pdf(content: bytes) -> str:
    """Extract text from a PDF file."""
    reader = PdfReader(io.BytesIO(content))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def parse_docx(content: bytes) -> str:
    """Extract text from a DOCX file."""
    doc = Document(io.BytesIO(content))
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def read_google_sheet(sheet_id: str, range_name: str = None) -> List[Dict[str, Any]]:
    """Read data from a Google Sheet and return as a list of dictionaries."""
    client = get_gsheets_client()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.get_worksheet(0)  # Default to first sheet
    
    if range_name:
        data = worksheet.get(range_name)
        if not data:
            return []
        headers = data[0]
        rows = data[1:]
        return [dict(zip(headers, row)) for row in rows]
    else:
        return worksheet.get_all_records()

def find_ticker_in_sheet(sheet_id: str, ticker: str, company_name: str = "") -> Dict[str, Any] | None:
    """
    Scans all worksheets in a Google Sheet for a ticker or company name.
    Priority is given to the latest worksheets (scanning in reverse order).
    """
    client = get_gsheets_client()
    try:
        sheet = client.open_by_key(sheet_id)
        worksheets = sheet.worksheets()
        
        # Scan worksheets in reverse (newest first)
        for worksheet in reversed(worksheets):
            try:
                records = worksheet.get_all_records()
            except Exception:
                all_vals = worksheet.get_all_values()
                if len(all_vals) > 1:
                    headers = [f"col_{i}" if not h.strip() else h for i, h in enumerate(all_vals[0])]
                    records = [dict(zip(headers, row)) for row in all_vals[1:]]
                else:
                    records = []
            if not records:
                continue
            
            # Look for matches in any column that might contain Ticker or Company
            ticker_upper = ticker.upper()
            company_lower = (company_name or "").lower()
            
            for record in records:
                # Check for ticker match
                found = False
                for key, val in record.items():
                    val_str = str(val).strip()
                    if key.lower() in ("ticker", "symbol") and val_str.upper() == ticker_upper:
                        found = True
                        break
                    if company_lower and company_lower in val_str.lower():
                        found = True
                        break
                
                if found:
                    record["_sheet_source"] = worksheet.title
                    return record
    except Exception as e:
        print(f"Error searching sheet {sheet_id}: {str(e)}")
        
    return None

def get_company_data_from_latest_tab(sheet_id: str, ticker: str, company_name: str = "") -> List[Dict[str, Any]]:
    """
    Searches ONLY the latest (rightmost) tab for all rows matching the ticker or company name.
    """
    client = get_gsheets_client()
    try:
        sheet = client.open_by_key(sheet_id)
        worksheets = sheet.worksheets()
        if not worksheets:
            return []
        
        # Only the latest tab
        latest_tab = worksheets[-1]
        try:
            records = latest_tab.get_all_records()
        except Exception as _hdr_err:
            # Duplicate/empty header row — fall back to raw values and skip header
            all_vals = latest_tab.get_all_values()
            if len(all_vals) > 1:
                headers = [f"col_{i}" if not h.strip() else h for i, h in enumerate(all_vals[0])]
                records = [dict(zip(headers, row)) for row in all_vals[1:]]
            else:
                records = []
        
        matches = []
        ticker_upper = ticker.upper() if ticker else None
        company_lower = (company_name or "").lower()
        
        for record in records:
            found = False
            for key, val in record.items():
                val_str = str(val).strip()
                if ticker_upper and key.lower() in ("ticker", "symbol") and val_str.upper() == ticker_upper:
                    found = True
                    break
                if company_lower and company_lower in val_str.lower():
                    found = True
                    break
            if found:
                record["_sheet_source"] = latest_tab.title
                matches.append(record)
        return matches
    except Exception as e:
        import traceback
        print(f"Error searching latest tab in sheet {sheet_id} for ticker {ticker}: {repr(e)}")
        print(traceback.format_exc())
    return []

def get_company_data_from_tab_gid(sheet_id: str, tab_gid: int) -> List[Dict[str, Any]]:
    """
    Fetches ALL rows from a specific tab identified by its numeric GID.
    This is the most precise way to target a specific worksheet.
    """
    client = get_gsheets_client()
    try:
        sheet = client.open_by_key(sheet_id)
        worksheets = sheet.worksheets()
        
        target_ws = None
        for ws in worksheets:
            if ws.id == tab_gid:
                target_ws = ws
                break
        
        if not target_ws:
            print(f"[GDRIVE] Tab GID {tab_gid} not found in sheet {sheet_id}")
            return []
        
        print(f"[GDRIVE] Reading specific tab: '{target_ws.title}' (GID: {tab_gid})")
        try:
            records = target_ws.get_all_records()
        except Exception:
            all_vals = target_ws.get_all_values()
            if len(all_vals) > 1:
                headers = [f"col_{i}" if not h.strip() else h for i, h in enumerate(all_vals[0])]
                records = [dict(zip(headers, row)) for row in all_vals[1:]]
            else:
                records = []
        
        for r in records:
            r["_sheet_source"] = target_ws.title
        return records
        
    except Exception as e:
        import traceback
        print(f"Error reading tab GID {tab_gid} from sheet {sheet_id}: {repr(e)}")
        print(traceback.format_exc())
    return []


def get_company_data_from_matching_tab(sheet_id: str, ticker: str, company_name: str = "") -> List[Dict[str, Any]]:
    """
    Searches for a tab whose name matches the ticker or company name, and returns all rows from it.
    """
    client = get_gsheets_client()
    try:
        sheet = client.open_by_key(sheet_id)
        worksheets = sheet.worksheets()
        
        ticker_lower = ticker.lower() if ticker else None
        company_lower = (company_name or "").lower()
        
        for worksheet in worksheets:
            title_lower = worksheet.title.lower().strip()
            # Match tab name to ticker or company
            if (ticker_lower and title_lower == ticker_lower) or (company_lower and company_lower in title_lower):
                records = worksheet.get_all_records()
                for r in records:
                    r["_sheet_source"] = worksheet.title
                return records
    except Exception as e:
        import traceback
        print(f"Error searching matching tab in sheet {sheet_id} for ticker {ticker}: {repr(e)}")
        print(traceback.format_exc())
    return []

def get_latest_report_content(folder_id: str) -> str:
    """Identifies the latest file in a folder and returns its parsed text."""
    files = list_files_in_folder(folder_id, sort_by_newest=True)
    if not files:
        return "No reports found in folder."
    
    latest = files[0]
    file_id = latest['id']
    name = latest['name']
    mime_type = latest['mimeType']
    
    try:
        if mime_type == 'application/pdf':
            content = download_file_content(file_id, mime_type)
            text = parse_pdf(content)
            return f"--- LATEST REPORT: {name} (PDF) ---\n{text}"
        elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.google-apps.document']:
            content = download_file_content(file_id, mime_type)
            text = parse_docx(content)
            return f"--- LATEST REPORT: {name} (DOCX) ---\n{text}"
        elif mime_type in ['application/vnd.google-apps.spreadsheet', 'text/csv']:
            client = get_gsheets_client()
            sheet = client.open_by_key(file_id)
            all_text = []
            for worksheet in sheet.worksheets():
                df = pd.DataFrame(worksheet.get_all_records())
                all_text.append(f"Sheet: {worksheet.title}\n{df.to_string()}")
            return f"--- LATEST REPORT: {name} (Spreadsheet) ---\n" + "\n".join(all_text)
    except Exception as e:
        return f"Error parsing latest report {name}: {str(e)}"
    
    return f"Unsupported file type for latest report: {mime_type}"

def get_research_context(folder_id: str) -> str:
    """Compile research context from all files in a folder (legacy support)."""
    files = list_files_in_folder(folder_id)
    combined_context = []
    
    for file in files:
        name = file['name']
        mime_type = file['mimeType']
        file_id = file['id']
        
        try:
            if mime_type == 'application/pdf':
                content = download_file_content(file_id, mime_type)
                text = parse_pdf(content)
                combined_context.append(f"--- SOURCE: {name} (PDF) ---\n{text}")
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.google-apps.document']:
                content = download_file_content(file_id, mime_type)
                text = parse_docx(content)
                combined_context.append(f"--- SOURCE: {name} (DOCX) ---\n{text}")
            elif mime_type in ['application/vnd.google-apps.spreadsheet', 'text/csv']:
                client = get_gsheets_client()
                sheet = client.open_by_key(file_id)
                all_text = []
                for worksheet in sheet.worksheets():
                    df = pd.DataFrame(worksheet.get_all_records())
                    all_text.append(f"Sheet: {worksheet.title}\n{df.to_string()}")
                combined_context.append(f"--- SOURCE: {name} (Spreadsheet) ---\n" + "\n".join(all_text))
        except Exception as e:
            combined_context.append(f"--- SOURCE: {name} --- ERROR: Could not parse: {str(e)}")
            
    return "\n\n".join(combined_context)
