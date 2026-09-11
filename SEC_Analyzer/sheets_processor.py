import gspread
from google.oauth2.service_account import Credentials
import os
import time
from dotenv import load_dotenv

load_dotenv()

class SheetsProcessor:
    def __init__(self):
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
        self.creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        self.client = gspread.authorize(self.creds)
        self.source_id = os.getenv('SOURCE_SHEET_ID')
        self.target_id = os.getenv('TARGET_SHEET_ID')

        self.source_spreadsheet = self.client.open_by_key(self.source_id)
        self.target_spreadsheet = self.client.open_by_key(self.target_id)

    # ------------------------------------------------------------------ #
    #  Reading                                                            #
    # ------------------------------------------------------------------ #

    def get_all_tickers_by_tab(self) -> dict:
        """
        Reads ALL columns from each sector tab in the source spreadsheet.
        Returns a dict of {tab_name: [full_row_dict, ...]}.
        Skips tabs named Summary / Info / Dashboard.
        """
        all_tabs_data = {}
        skip_tabs = {'summary', 'info', 'dashboard'}

        for worksheet in self.source_spreadsheet.worksheets():
            tab_name = worksheet.title
            if tab_name.lower() in skip_tabs:
                print(f"Skipping non-ticker tab: {tab_name}")
                continue

            print(f"Reading tab: {tab_name}")
            try:
                records = worksheet.get_all_records()  # list of full row dicts
            except Exception as e:
                print(f"  Could not read tab {tab_name}: {e}")
                continue

            tickers_in_tab = []
            for row in records:
                # Support multiple possible column name conventions
                ticker = (
                    row.get('ticker') or row.get('Ticker') or
                    row.get('SYMBOL') or row.get('Symbol') or ''
                )
                name = (
                    row.get('company_name') or row.get('Name') or
                    row.get('Description') or row.get('Company') or ''
                )
                ticker = str(ticker).strip()
                name   = str(name).strip()

                if ticker:
                    # Pass the FULL row dict through so the analyzer can use
                    # pre-computed ratios, EC summaries, sentiment, etc.
                    row_copy = dict(row)
                    row_copy['ticker'] = ticker
                    row_copy['name']   = name
                    row_copy['sector'] = row_copy.get('sector') or tab_name
                    tickers_in_tab.append(row_copy)

            if tickers_in_tab:
                all_tabs_data[tab_name] = tickers_in_tab
                print(f"  Found {len(tickers_in_tab)} tickers")

        return all_tabs_data

    # ------------------------------------------------------------------ #
    #  Writing                                                            #
    # ------------------------------------------------------------------ #

    def ensure_tab_exists(self, tab_name: str):
        """Returns an existing (cleared) tab or creates a new one."""
        try:
            worksheet = self.target_spreadsheet.worksheet(tab_name)
            worksheet.clear()
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            print(f"  Creating new tab: {tab_name}")
            return self.target_spreadsheet.add_worksheet(title=tab_name, rows="200", cols="30")

    def write_tab_data(self, tab_name: str, headers: list, rows: list):
        """Writes headers + rows to a tab in the target sheet."""
        worksheet = self.ensure_tab_exists(tab_name)

        if headers:
            worksheet.append_row(headers, value_input_option='RAW')
        if rows:
            worksheet.append_rows(rows, value_input_option='RAW')
            print(f"  Wrote {len(rows)} rows to '{tab_name}'")

        # Brief pause to respect Google Sheets API rate limits
        time.sleep(1)

    def write_summary_tab(self, summary_rows: list):
        """
        Writes a sector-level summary tab to the target sheet.
        summary_rows: list of dicts with keys:
            sector, total_tickers, avg_f_score, avg_z_score,
            bullish_count, bearish_count, neutral_count
        """
        headers = [
            'Sector', 'Total Tickers', 'Avg F-Score', 'Avg Z-Score',
            'Bullish Count', 'Bearish Count', 'Neutral Count'
        ]
        rows = []
        for r in summary_rows:
            rows.append([
                r.get('sector', ''),
                r.get('total_tickers', 0),
                r.get('avg_f_score', ''),
                r.get('avg_z_score', ''),
                r.get('bullish_count', 0),
                r.get('bearish_count', 0),
                r.get('neutral_count', 0),
            ])
        self.write_tab_data('Summary', headers, rows)


if __name__ == "__main__":
    processor = SheetsProcessor()
    data = processor.get_all_tickers_by_tab()
    for tab, tickers in data.items():
        print(f"Tab '{tab}': {len(tickers)} tickers")
        if tickers:
            # Show which columns we have
            print(f"  Columns: {list(tickers[0].keys())}")
