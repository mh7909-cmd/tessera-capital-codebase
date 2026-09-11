import os
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from gspread_formatting import (
    format_cell_range, CellFormat, TextFormat, Color, 
    set_column_width, set_row_height
)

load_dotenv()

class PipelineHandoff:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        self.creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
        self.queue_sheet_id = os.getenv("PIPELINE_QUEUE_ID") or os.getenv("MASTER_SHEET_ID")
        self.gc = self._authenticate()

    def _authenticate(self):
        if not os.path.exists(self.creds_path):
            raise FileNotFoundError(f"Google Credentials not found at {self.creds_path}")
        creds = Credentials.from_service_account_file(self.creds_path, scopes=self.scopes)
        return gspread.authorize(creds)

    def prepare_queue_sheet(self, sheet_name="Pipeline Queue"):
        sh = self.gc.open_by_key(self.queue_sheet_id)
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            print(f"Creating '{sheet_name}' tab...")
            worksheet = sh.add_worksheet(title=sheet_name, rows="1000", cols="20")
            worksheet.append_row(["Ticker", "Position Lean", "Conviction Score", "Confidence Interval", "Strategic Rationale", "Contradictions", "Status"])
            
            # Formatting
            format_cell_range(worksheet, "1:1", CellFormat(
                backgroundColor=Color(0.1, 0.1, 0.2),
                textFormat=TextFormat(foregroundColor=Color(1, 1, 1), bold=True),
                horizontalAlignment="CENTER",
                verticalAlignment="MIDDLE"
            ))
            worksheet.freeze(rows=1)
            set_row_height(worksheet, "1", 40)
            set_row_height(worksheet, "2:1000", 50)
            
            set_column_width(worksheet, "A", 80)   # Ticker
            set_column_width(worksheet, "B", 120)  # Lean
            set_column_width(worksheet, "C", 120)  # Score
            set_column_width(worksheet, "D", 150)  # CI
            set_column_width(worksheet, "E", 750)  # Rationale
            set_column_width(worksheet, "F", 400)  # Contradictions

            for i in range(2, 101, 2):
                format_cell_range(worksheet, f"A{i}:G{i}", CellFormat(backgroundColor=Color(0.96, 0.97, 0.98)))
            
            format_cell_range(worksheet, "A2:G1000", CellFormat(verticalAlignment="MIDDLE", wrapStrategy="WRAP"))
            
        return worksheet

    def push_state_to_queue(self, state_path="thesis_state.json", threshold=0.65):
        if not os.path.exists(state_path):
            print("No state found to push.")
            return

        with open(state_path, "r") as f:
            state = json.load(f)

        worksheet = self.prepare_queue_sheet()
        rows_to_add = []
        skipped = []
        
        for ticker, data in state.items():
            score = data.get("conviction_score", 0)
            lean = data.get("final_lean", "Neutral")
            
            if score >= threshold and lean != "Neutral":
                rows_to_add.append([
                    ticker,
                    lean,
                    score,
                    str(data.get("confidence_interval", [])),
                    data.get("strategic_rationale", ""),
                    ", ".join(data.get("contradictions_found", [])),
                    "pending"
                ])
            else:
                skipped.append(f"{ticker} ({score}, {lean})")

        if rows_to_add:
            worksheet.append_rows(rows_to_add)
            print(f"✅ Handoff complete. {len(rows_to_add)} targets pushed to Queue.")
        if skipped:
            print(f"ℹ️ Skipped {len(skipped)} low-conviction targets: {', '.join(skipped[:5])}...")

if __name__ == "__main__":
    handoff = PipelineHandoff()
    handoff.push_state_to_queue()
