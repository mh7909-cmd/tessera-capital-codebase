import os
import sys
import gspread
import gspread_formatting as gs_fmt
import time
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

# ── Color palette (mirrors sheets_utils.py institutional aesthetic) ──────────
C_HEADER_BG  = gs_fmt.Color(0.05, 0.05, 0.12)   # Near-black navy (like INDIGO block)
C_WHITE      = gs_fmt.Color(1.0,  1.0,  1.0)
C_OFF_WHITE  = gs_fmt.Color(0.96, 0.97, 0.98)
C_STRIPE     = gs_fmt.Color(0.93, 0.94, 0.96)
C_SENT_BG    = gs_fmt.Color(0.88, 0.96, 0.88)   # Soft green for "sent"
C_SENT_FG    = gs_fmt.Color(0.10, 0.45, 0.15)   # Dark green text
C_PENDING_BG = gs_fmt.Color(1.00, 0.97, 0.88)   # Soft amber for "pending"
C_PENDING_FG = gs_fmt.Color(0.55, 0.35, 0.00)   # Dark amber text


def _apply_leads_formatting(leads_ws, num_data_rows: int):
    """Apply institutional-grade formatting to the Leads tab in one batched call."""
    sheet_id = int(leads_ws.id)
    total_rows = 1 + num_data_rows   # header + data

    requests = []

    # 1. Column widths: Name, Company, Role, Email, Topic, Status
    col_widths = [180, 200, 220, 240, 280, 90]
    for i, w in enumerate(col_widths):
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                          "startIndex": i, "endIndex": i + 1},
                "properties": {"pixelSize": w},
                "fields": "pixelSize"
            }
        })

    # 2. Row heights — header taller, data rows comfortable
    requests.append({
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "ROWS",
                      "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 36},
            "fields": "pixelSize"
        }
    })
    requests.append({
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "ROWS",
                      "startIndex": 1, "endIndex": total_rows},
            "properties": {"pixelSize": 30},
            "fields": "pixelSize"
        }
    })

    # 3. Global font — Lexend 10pt, wrap, top-align (all cells)
    requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id,
                      "startRowIndex": 0, "endRowIndex": total_rows,
                      "startColumnIndex": 0, "endColumnIndex": 6},
            "cell": {"userEnteredFormat": {
                "textFormat": {"fontFamily": "Lexend", "fontSize": 10},
                "verticalAlignment": "MIDDLE",
                "wrapStrategy": "WRAP"
            }},
            "fields": "userEnteredFormat(textFormat,verticalAlignment,wrapStrategy)"
        }
    })

    # 4. Header row — dark navy bg, white bold text, center-aligned
    requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id,
                      "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": 6},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.05, "green": 0.05, "blue": 0.12},
                "textFormat": {
                    "fontFamily": "Lexend", "fontSize": 10,
                    "bold": True,
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}
                },
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE"
            }},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
        }
    })

    # 5. Freeze header row
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 1}
            },
            "fields": "gridProperties.frozenRowCount"
        }
    })

    # 6. Alternating row stripes for data rows
    for i in range(num_data_rows):
        row_idx = i + 1   # 0-based, skip header
        bg = {"red": 0.96, "green": 0.97, "blue": 0.98} if i % 2 == 0 else {"red": 0.93, "green": 0.94, "blue": 0.96}
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id,
                          "startRowIndex": row_idx, "endRowIndex": row_idx + 1,
                          "startColumnIndex": 0, "endColumnIndex": 5},  # all except Status
                "cell": {"userEnteredFormat": {
                    "backgroundColor": bg
                }},
                "fields": "userEnteredFormat.backgroundColor"
            }
        })

    # 7. Status column (col F, index 5) — color-code each cell
    # Mark as "Sent" (Green) or "Pending" (Amber)
    for i in range(num_data_rows):
        row_idx = i + 1
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id,
                          "startRowIndex": row_idx, "endRowIndex": row_idx + 1,
                          "startColumnIndex": 5, "endColumnIndex": 6},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.88, "green": 0.96, "blue": 0.88}, # Sent (Green)
                    "textFormat": {
                        "fontFamily": "Lexend", "fontSize": 10, "bold": True,
                        "foregroundColor": {"red": 0.10, "green": 0.45, "blue": 0.15}
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                }},
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
            }
        })

    # 8. Outer border on the whole table (top/bottom/left/right + inner grid)
    _outer = {"style": "SOLID_MEDIUM", "color": {"red": 0.05, "green": 0.05, "blue": 0.12}}
    _inner = {"style": "SOLID",        "color": {"red": 0.85, "green": 0.86, "blue": 0.88}}
    requests.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id,
                      "startRowIndex": 0, "endRowIndex": total_rows,
                      "startColumnIndex": 0, "endColumnIndex": 6},
            "top":             _outer,
            "bottom":          _outer,
            "left":            _outer,
            "right":           _outer,
            "innerHorizontal": _inner,
            "innerVertical":   _inner,
        }
    })

    leads_ws.spreadsheet.batch_update({"requests": requests})


def apply_row_formatting(leads_ws, row_idx: int, is_sent: bool = False):
    """Apply institutional-grade formatting to a specific data row (Kinetic Mode)."""
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


def inject_fly_leads():
    print("🚀 [KINETIC_SYNC] Injecting Firefly Aerospace expert roster...")

    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)

    pipe_sh = gc.open_by_key(os.getenv('PIPELINE_SHEET_ID'))

    # Get or create the Leads tab
    try:
        leads_ws = pipe_sh.worksheet('Leads')
    except Exception:
        leads_ws = pipe_sh.add_worksheet(title='Leads', rows='100', cols='10')
        print("   [✓] Created 'Leads' tab in Pipeline Sheet.")

    # Clear existing data (keep tab)
    leads_ws.clear()

    # Hollywood expert roster — all routed to demo inbox
    headers = ["Name", "Company", "Role", "Email", "Topic", "Status"]
    leads = [
        ["Shubhanker Kapoor",    "Impulse Space",          "Lead, Propulsion Systems",          "s.kapoor@impulsespace.com", "Propulsion Systems & Reaver engine reliability",        "sent"],
        ["Khaled Moharam",       "PulseForge, Inc.",        "Lead Power Systems Engineer",        "k.moharam@pulseforge.com", "Power Systems integration for Launch Vehicles",         "sent"],
        ["Isaac Browne",         "Bechtel Corporation",     "Launch Vehicle Systems Engineer",    "i.browne@bechtel.com", "Launch Systems & Ground Support Equipment",             "sent"],
        ["Brandon Reemsnyder",   "PLD Space",               "Propulsion Engineer II",             "b.reemsnyder@pldspace.com", "Propulsion Design & manufacturing throughput",          "sent"],
        ["Kyle Hillman",         "SpaceX",                  "Propulsion Engineer",               "k.hillman@spacex.com", "Launch Engineering & manufacturing thresholds",          "sent"],
        ["Jacob Frogget",        "Cadence Design Systems",  "Senior FPGA Engineer",              "j.frogget@cadence.com", "Avionics Hardware & mission-level reliability",          "sent"],
    ]

    # 1. Write headers immediately
    leads_ws.update("A1:F1", [headers], value_input_option="RAW")
    # Apply global formatting skeleton (width, font, etc)
    _apply_leads_formatting(leads_ws, 0) # Format header only
    
    # 2. Kinetic Row Injection: One by one with a cinematic pause
    for i, lead in enumerate(leads):
        row_idx = i + 1 # 1-based index for GSheets (header is 0 for indices, row 1)
        print(f"   ⌨️  [KINETIC] Synchronizing lead: {lead[0]} ({lead[1]})...")
        
        # Add row with "pending" status (Institutional Amber)
        display_lead = lead.copy()
        display_lead[5] = "pending"
        
        # Batch the update to reduce API calls
        leads_ws.update(f"A{row_idx+1}:F{row_idx+1}", [display_lead], value_input_option="RAW")
        apply_row_formatting(leads_ws, row_idx, is_sent=False)
        
        # 2-second sleep ensures we stay WELL under the 60 requests/minute quota
        time.sleep(2.0)

    print(f"   ✨ [SUCCESS] Injected {len(leads)} expert leads into 'Leads' tab.")
    print(f"   🎯 Prepared for direct institutional outreach.")


if __name__ == "__main__":
    inject_fly_leads()
