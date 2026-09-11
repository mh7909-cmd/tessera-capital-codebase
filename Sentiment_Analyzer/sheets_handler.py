import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class SheetsHandler:
    def __init__(self, target_tab_name=None):
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        # Use root credentials if possible
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
        if not os.path.exists(creds_path):
            # Try parent directory for orchestrator runs
            creds_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
            
        self.creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        self.client = gspread.authorize(self.creds)
        
        # Dual-Sheet Architecture:
        # source_id = Sheet A (The Screener Master)
        # target_id = Sheet B (The Sentiment Dashboard)
        self.source_id = os.getenv('MASTER_SHEET_ID')
        self.target_id = os.getenv('SENTIMENT_SHEET_ID') or self.source_id
        
        self.target_tab_name = target_tab_name
        self.current_run_worksheet = None


    def get_all_tickers(self, tab_override=None):
        """Reads the specified tab or latest date tab from the source sheet."""
        sheet = self.client.open_by_key(self.source_id)
        
        target_ws = None
        if tab_override:
            try:
                target_ws = sheet.worksheet(tab_override)
            except gspread.exceptions.WorksheetNotFound:
                print(f"Warning: Tab '{tab_override}' not found in source sheet.")
        
        if not target_ws:
            latest_date = None
            for worksheet in sheet.worksheets():
                title = worksheet.title
                try:
                    tab_date = datetime.strptime(title, "%Y-%m-%d").date()
                    if latest_date is None or tab_date > latest_date:
                        latest_date = tab_date
                        target_ws = worksheet
                except ValueError:
                    continue
                    
        if not target_ws:
            print("Warning: No viable tabs found in source sheet.")
            return []
            
        print(f"Reading tickers from tab: {target_ws.title}")
        all_data = []
        records = target_ws.get_all_records()
        for row in records:
            ticker = row.get('ticker') or row.get('Ticker') or row.get('SYMBOL') or row.get('Symbol')
            name = row.get('company_name') or row.get('Name') or row.get('Description') or row.get('Company')
            if ticker:
                all_data.append({
                    'ticker': str(ticker).strip(),
                    'name': str(name).strip() if name else '',
                    'sector': row.get('sector', target_ws.title)
                })
        
        return all_data

    def update_ticker_live(self, analysis_result):
        """Updates sentiment columns for a specific ticker in the current worksheet (Sheet B)."""
        if not self.target_tab_name:
            # Fallback to latest date worksheet title or today's date
            try:
                sheet = self.client.open_by_key(self.target_id)
                latest_date = None
                latest_ws = None
                for worksheet in sheet.worksheets():
                    title = worksheet.title
                    try:
                        tab_date = datetime.strptime(title, "%Y-%m-%d").date()
                        if latest_date is None or tab_date > latest_date:
                            latest_date = tab_date
                            latest_ws = worksheet
                    except ValueError:
                        continue
                if latest_ws:
                    self.target_tab_name = latest_ws.title
                else:
                    self.target_tab_name = datetime.now().strftime("%Y-%m-%d")
            except Exception as e:
                self.target_tab_name = datetime.now().strftime("%Y-%m-%d")
            print(f"SheetsHandler: target_tab_name fell back to: {self.target_tab_name}")

        sheet = self.client.open_by_key(self.target_id)
        
        # Initialize tab if missing in Sheet B
        if not self.current_run_worksheet:
            try:
                self.current_run_worksheet = sheet.worksheet(self.target_tab_name)
            except gspread.exceptions.WorksheetNotFound:
                print(f"Creating new Sentiment tab in Sheet B: {self.target_tab_name}")
                self.current_run_worksheet = sheet.add_worksheet(title=self.target_tab_name, rows="1000", cols="10")
                headers = ["Ticker", "Name", "Social Sentiment Score", "Social Signal", "Social Summary"]
                self.current_run_worksheet.append_row(headers)
                
                # --- PERFECT SPACING & FORMATTING (Sheet B) ---
                from gspread_formatting import (
                    format_cell_range, CellFormat, TextFormat, Color, 
                    set_column_width, VerticalAlignment
                )
                
                # 1. Header Formatting
                format_cell_range(self.current_run_worksheet, "A1:E1", CellFormat(
                    backgroundColor=Color(0.1, 0.1, 0.2),
                    textFormat=TextFormat(foregroundColor=Color(1, 1, 1), bold=True),
                    horizontalAlignment="CENTER",
                    verticalAlignment="MIDDLE"
                ))
                
                # 2. Row Height & Freezing
                self.current_run_worksheet.freeze(rows=1)
                from gspread_formatting import set_row_height
                set_row_height(self.current_run_worksheet, "1", 40)
                set_row_height(self.current_run_worksheet, "2:1000", 50) # Spacious rows
                
                # 3. Column Widths
                set_column_width(self.current_run_worksheet, "A", 80)   # Ticker
                set_column_width(self.current_run_worksheet, "B", 280)  # Name
                set_column_width(self.current_run_worksheet, "C", 130)  # Score
                set_column_width(self.current_run_worksheet, "D", 130)  # Signal
                set_column_width(self.current_run_worksheet, "E", 700)  # Summary
                
                # 4. Zebra Banding (Alternating rows)
                for i in range(2, 101, 2):
                    format_cell_range(self.current_run_worksheet, f"A{i}:E{i}", CellFormat(
                        backgroundColor=Color(0.96, 0.97, 0.98)
                    ))

                # 5. Text Wrapping & Global Alignment
                format_cell_range(self.current_run_worksheet, "A2:E1000", CellFormat(
                    verticalAlignment="MIDDLE",
                    horizontalAlignment="LEFT",
                    wrapStrategy="WRAP"
                ))

        ws = self.current_run_worksheet

        headers = ws.row_values(1)
        
        try:
            score_col = headers.index("Social Sentiment Score") + 1
            signal_col = headers.index("Social Signal") + 1
            summary_col = headers.index("Social Summary") + 1
            name_col = headers.index("Name") + 1
        except ValueError:
            print("Warning: Headers missing in Sentiment Sheet B.")
            return False

        ticker = analysis_result.get('ticker')
        tickers_col = ws.col_values(1) 
        
        try:
            row_idx = tickers_col.index(ticker) + 1
        except ValueError:
            # Ticker not in Sheet B yet, let's append it
            print(f"   + Adding {ticker} to Sentiment Sheet B")
            ws.append_row([ticker, analysis_result.get('name', ''), '', '', ''])
            # Refresh row_idx
            tickers_col = ws.col_values(1)
            row_idx = len(tickers_col)

        # Prepare updates
        updates = [
            {'range': gspread.utils.rowcol_to_a1(row_idx, score_col), 'values': [[analysis_result.get('sentiment_score', 0)]]},
            {'range': gspread.utils.rowcol_to_a1(row_idx, signal_col), 'values': [[analysis_result.get('bull_bear', 'Neutral')]]},
            {'range': gspread.utils.rowcol_to_a1(row_idx, summary_col), 'values': [[analysis_result.get('summary', '')]]}
        ]
        ws.batch_update(updates)
        print(f"   ✓ [Live Update] Wrote social data for {ticker} to Sheet B.")
        return True


    def write_analysis(self, results):
        """Legacy batch write support."""
        if not results: return
        for res in results:
            self.update_ticker_live(res)


if __name__ == "__main__":
    handler = SheetsHandler()
    tickers = handler.get_all_tickers()
    print(f"Found {len(tickers)} tickers from the latest tab.")
    for t in tickers[:5]:
        print(t)
