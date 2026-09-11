import gspread
from google.oauth2.service_account import Credentials
import json
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    # Load mass_diligence data
    input_path = os.path.join(os.path.dirname(__file__), "mass_diligence.json")
    if not os.path.exists(input_path):
        print(f"❌ Error: {input_path} not found. Run nemotron_analysis.py first.")
        return

    with open(input_path, "r") as f:
        data = json.load(f)

    if not data:
        print("⚠️ No research targets to push.")
        return

    # Auth
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
    
    # Robust path check for orchestrator runs
    if not os.path.exists(creds_path):
        parent_creds = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
        if os.path.exists(parent_creds):
            creds_path = parent_creds
            
    if not os.path.exists(creds_path):
        print(f"❌ Error: Google Credentials not found at {creds_path}")
        return

    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    
    # Open Pipeline Queue Sheet
    # Usually we push this to the Master Sheet or a dedicated Queue Sheet
    # The user's env has PIPELINE_QUEUE_ID
    queue_sheet_id = os.getenv("PIPELINE_QUEUE_ID") or os.getenv("MASTER_SHEET_ID")
    
    try:
        sh = gc.open_by_key(queue_sheet_id)
        try:
            worksheet = sh.worksheet("Pipeline Queue")
        except gspread.WorksheetNotFound:
            print("Creating 'Pipeline Queue' tab...")
            worksheet = sh.add_worksheet(title="Pipeline Queue", rows="1000", cols="20")
            worksheet.append_row(["Ticker", "Company", "Position Lean", "Primary Diligence Aspect", "Detailed Strategic Rationale", "Status"])
            
            # --- ULTRA-PREMIUM FORMATTING ---
            from gspread_formatting import (
                format_cell_range, CellFormat, TextFormat, Color, 
                set_column_width, set_row_height
            )
            
            # 1. Header Formatting (Dark Indigo)
            format_cell_range(worksheet, "1:1", CellFormat(
                backgroundColor=Color(0.1, 0.1, 0.2),
                textFormat=TextFormat(foregroundColor=Color(1, 1, 1), bold=True),
                horizontalAlignment="CENTER",
                verticalAlignment="MIDDLE"
            ))
            
            # 2. Row Height & Freezing
            worksheet.freeze(rows=1)
            set_row_height(worksheet, "1", 40)
            set_row_height(worksheet, "2:1000", 50)
            
            # 3. Column Widths
            set_column_width(worksheet, "A", 80)   # Ticker
            set_column_width(worksheet, "B", 250)  # Company
            set_column_width(worksheet, "C", 120)  # Lean
            set_column_width(worksheet, "D", 250)  # Aspect
            set_column_width(worksheet, "E", 750)  # Strategic Rationale (Extra Wide)
            
            # 4. Zebra Banding
            for i in range(2, 101, 2):
                format_cell_range(worksheet, f"A{i}:F{i}", CellFormat(
                    backgroundColor=Color(0.96, 0.97, 0.98)
                ))
            
            # 5. Global Text Wrapping
            format_cell_range(worksheet, "A2:F1000", CellFormat(
                verticalAlignment="MIDDLE",
                wrapStrategy="WRAP"
            ))

        print(f"Pushing {len(data)} research targets to Pipeline Queue...")
        
        rows_to_add = []
        for item in data:
            rows_to_add.append([
                item.get("ticker", "UNKNOWN"),
                item.get("company_name", item.get("company", "UNKNOWN")),
                item.get("final_lean", "Neutral"),
                item.get("diligence_objective", "Pending"),
                item.get("strategic_rationale", ""), 
                "pending"
            ])
        
        if rows_to_add:
            worksheet.append_rows(rows_to_add)
            print("✅ Handoff complete. Research targets are live in Pipeline Queue.")
        
    except Exception as e:
        print(f"❌ Failed to append to Pipeline Queue: {e}")

if __name__ == "__main__":
    main()
