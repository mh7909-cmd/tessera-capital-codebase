"""
Production Runner for AI Equity Screening Agent
Orchestrates data ingestion, screening, and output generation.
"""

import sys
import argparse
from datetime import datetime
import pandas as pd
from pathlib import Path

try:
    import gspread
    from gspread_dataframe import set_with_dataframe
except ImportError:
    pass

# Import our modules
from equity_screener_agent import EquityScreenerAgent, GICS_SECTORS
from data_ingestion import YFinanceProvider, SECFilingsProvider, get_sp500_tickers
from nlp_analysis import TranscriptAnalyzer, AnomalyDetector


class ProductionScreener:
    """
    Production-ready screening orchestrator.
    Handles full pipeline from data ingestion to final output.
    """
    
    def __init__(self, data_source: str = "yfinance", output_dir: str = "outputs/"):
        self.data_source = data_source
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        self.min_mcap = 1e9  # $1B
        self.max_mcap = 50e9  # $50B
        
        # Google Sheets configuration (Hardcoded default)
        self.google_folder_id = "1B6shb7SZXVu6D-SPTyoUm9VJoFAkQmK3"
        self.google_creds = None
        
        # Initialize components
        self.data_provider = None
        self.agent = None
        
    def run_full_pipeline(self):
        """Execute complete screening pipeline with live Google Sheet updates."""
        
        print("="*80)
        print("AI-NATIVE FUNDAMENTAL EQUITY SCREENING AGENT")
        print("="*80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Market Cap Range: ${self.min_mcap/1e9:.1f}B - ${self.max_mcap/1e9:.1f}B")
        print(f"Data Source: {self.data_source}")
        print("="*80)
        
        # Step 1: Load universe
        universe_df = self._load_universe()
        
        if len(universe_df) == 0:
            print("\nERROR: No stocks in universe. Check data source configuration.")
            return
        
        print(f"\n✓ Universe loaded: {len(universe_df)} stocks")
        print(f"  Sectors represented: {universe_df['sector'].nunique()}")
        
        # Step 2: Initialize screening agent
        self.agent = EquityScreenerAgent(self.min_mcap, self.max_mcap)
        self.agent.universe = universe_df

        # Step 2.5: Prepare Google Sheet for Live Updates
        worksheet = None
        master_sheet_id = None
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        master_sheet_id = os.getenv("MASTER_SHEET_ID")
        creds_path = self.google_creds or "client_secret.json"
        
        # Robust pathing: if not in CWD, look in one level up (root)
        if not os.path.exists(creds_path):
            root_creds = os.path.join("..", creds_path)
            if os.path.exists(root_creds):
                creds_path = root_creds

        if master_sheet_id and os.path.exists(creds_path):
            print(f"\n📡 Preparing Master Sheet (ID: {master_sheet_id}) for live updates...")
            try:
                auth_user_path = Path(creds_path).parent / "authorized_user.json"
                gc = gspread.oauth(
                    credentials_filename=creds_path,
                    authorized_user_filename=str(auth_user_path)
                )
                sh = gc.open_by_key(master_sheet_id)
                
                # Create a new tab for this run
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tab_name = datetime.now().strftime("%Y-%m-%d")
                existing_tabs = [ws.title for ws in sh.worksheets()]
                
                counter = 1
                base_tab_name = tab_name
                while tab_name in existing_tabs:
                    counter += 1
                    tab_name = f"{base_tab_name} Run {counter}"
                
                print(f"✅ Created Live Tab: '{tab_name}'")
                worksheet = sh.add_worksheet(title=tab_name, rows="1000", cols="30")

                # Define Super Dashboard headers — full financial stack + EC analysis
                headers = [
                    "ticker", "company_name", "sector", "industry",
                    "market_cap", "enterprise_value", "price",
                    "pe_ratio", "forward_pe", "peg_ratio",
                    "price_to_book", "ev_to_ebitda", "ev_to_revenue",
                    "profit_margin", "gross_margin", "ebitda_margin",
                    "roe", "roa", "revenue_growth", "earnings_growth",
                    "current_ratio", "debt_to_equity", "fcf", "operating_cashflow",
                    "qual_score",
                    "EC 1 Summary", "EC 2 Summary", "EC 3 Summary", "EC 4 Summary", "Overall Sentiment"
                ]
                worksheet.append_row(headers)
                
                from gspread_formatting import (
                    format_cell_range, CellFormat, TextFormat, Color, 
                    set_column_width, set_row_height,
                    VerticalAlignment, HorizontalAlignment, NumberFormat
                )
                
                # 1. Header Formatting (Dark Indigo)
                format_cell_range(worksheet, "A1:AD1", CellFormat(
                    backgroundColor=Color(0.1, 0.1, 0.2),
                    textFormat=TextFormat(foregroundColor=Color(1, 1, 1), bold=True),
                    horizontalAlignment="CENTER",
                    verticalAlignment="MIDDLE"
                ))
                
                # 2. Global Row Spacing & Freezing
                worksheet.freeze(rows=1)
                set_row_height(worksheet, "1", 40) # Header height
                set_row_height(worksheet, "2:1000", 50) # Data height (spacious)
                
                # 3. Column Widths (Horizontal Spacing)
                set_column_width(worksheet, "A", 80)   # Ticker (Widened)
                set_column_width(worksheet, "B", 280)  # Name
                set_column_width(worksheet, "C:D", 160) # Sector/Industry
                set_column_width(worksheet, "E:Y", 100)  # Financials
                set_column_width(worksheet, "Z:AC", 600) # EC Summaries (Extra wide for reading)
                set_column_width(worksheet, "AD", 180) # Sentiment
                
                # 4. Text Wrapping & Multi-Line Centering
                format_cell_range(worksheet, "A2:AD1000", CellFormat(
                    verticalAlignment="MIDDLE",
                    horizontalAlignment="LEFT",
                    wrapStrategy="WRAP"
                ))

                # 5. Zebra Banding (Alternating row colors for scanning)
                from gspread_formatting import set_row_height
                for i in range(2, 100, 2): # Apply banding to top 100 rows
                    format_cell_range(worksheet, f"A{i}:AD{i}", CellFormat(
                        backgroundColor=Color(0.96, 0.97, 0.98) # Very subtle blue-grey
                    ))
                
                # 6. Number Formatting for Ratios/Metrics
                ratio_format = CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='#,##0.00'))
                format_cell_range(worksheet, "E2:Y1000", ratio_format)

            except Exception as e:
                print(f"⚠️  Sheet Initialization/Formatting failed: {e}")
                # Fallback removed - headers are already appended at the start of the try block.


        def live_update_callback(sector, top_10_df):
            """Callback to upload sector results as they are found to the Super Dashboard."""
            if worksheet:
                print(f"↗️  Live Upload: Pushing {len(top_10_df)} '{sector}' stocks to Google Sheets...")
                try:
                    import math
                    import pandas as pd
                    
                    def sanitize(val):
                        """Convert any non-JSON-safe value to an empty string."""
                        if val is None:
                            return 'N/A'
                        try:
                            if pd.isna(val):
                                return 'N/A'
                        except (TypeError, ValueError):
                            pass
                        try:
                            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                                return 'N/A'
                        except (TypeError, ValueError):
                            pass

                        return val
                    
                    rows = []
                    for _, row in top_10_df.iterrows():
                        rows.append([
                            sanitize(row.get('ticker', '')),
                            sanitize(row.get('company_name', '')),
                            sector,
                            sanitize(row.get('industry', '')),
                            sanitize(row.get('market_cap', '')),
                            sanitize(row.get('enterprise_value', '')),
                            sanitize(row.get('price', '')),
                            sanitize(row.get('pe_ratio', '')),
                            sanitize(row.get('forward_pe', '')),
                            sanitize(row.get('peg_ratio', '')),
                            sanitize(row.get('price_to_book', '')),
                            sanitize(row.get('ev_to_ebitda', '')),
                            sanitize(row.get('ev_to_revenue', '')),
                            sanitize(row.get('profit_margin', '')),
                            sanitize(row.get('gross_margin', '')),
                            sanitize(row.get('ebitda_margin', '')),
                            sanitize(row.get('roe', '')),
                            sanitize(row.get('roa', '')),
                            sanitize(row.get('revenue_growth', '')),
                            sanitize(row.get('earnings_growth', '')),
                            sanitize(row.get('current_ratio', '')),
                            sanitize(row.get('debt_to_equity', '')),
                            sanitize(row.get('fcf', '')),
                            sanitize(row.get('operating_cashflow', '')),
                            sanitize(row.get('qual_score', ''))
                        ])
                    
                    print(f"   → Prepared {len(rows)} rows. Uploading...")
                    worksheet.append_rows(rows, value_input_option='RAW')
                    print(f"   ✅ Upload complete for {sector}.")
                except Exception as e:
                    import traceback
                    print(f"⚠️  Live upload failed for {sector}: {e}")
                    traceback.print_exc()

        
        # Step 3: Run sector-by-sector screening with live updates
        print("\n" + "="*80)
        print("RUNNING SECTOR-BY-SECTOR SCREENING")
        print("="*80)
        
        results = self.agent.run_full_screen(callback=live_update_callback)
        
        # Step 4: Generate local records (but skip redundant Google Sheets export)
        print("\nSaving local records (CSV/Excel)...")
        self._generate_local_only_outputs(results)
        
        print("\n" + "="*80)
        print("SCREENING COMPLETE")
        print("="*80)
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return results, tab_name if worksheet else None

    def _generate_local_only_outputs(self, results):
        """Helper to generate local files without triggering a second sheet upload."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = self.output_dir / f"equity_screen_{timestamp}.xlsx"
        csv_path = self.output_dir / f"screening_summary_{timestamp}.csv"
        
        # Save Excel locally
        with pd.ExcelWriter(excel_path) as writer:
            for sector, df in results.items():
                if not df.empty:
                    df.to_excel(writer, sheet_name=sector[:31], index=False)
        
        # Save Summary CSV locally
        all_results = []
        for sector, df in results.items():
            for _, row in df.iterrows():
                all_results.append({'Sector': sector, **row.to_dict()})
        if all_results:
            pd.DataFrame(all_results).to_csv(csv_path, index=False)
        
        print(f"✓ Outputs generated locally in: {self.output_dir}")


    
    def _load_universe(self):
        """Load stock universe based on data source."""
        
        if self.data_source == "yfinance":
            return self._load_yfinance_universe()
        elif self.data_source == "capiq":
            return self._load_capiq_universe()
        elif self.data_source == "bloomberg":
            return self._load_bloomberg_universe()
        elif self.data_source == "csv":
            return self._load_csv_universe()
        else:
            raise ValueError(f"Unknown data source: {self.data_source}")
    
    def _load_yfinance_universe(self):
        """Load universe using Yahoo Finance (free, for development)."""
        print("\nLoading universe from Yahoo Finance...")
        print("(This may take several minutes)")
        
        # Get S&P 500 as starting point
        sp500_tickers = get_sp500_tickers()
        print(f"  Fetched {len(sp500_tickers)} S&P 500 tickers")
        
        # You could also add Russell 2000 here for more mid-cap coverage
        # russell_tickers = get_russell_2000_tickers()
        
        provider = YFinanceProvider()
        universe = provider.get_universe_from_list(
            sp500_tickers,
            min_mcap=self.min_mcap,
            max_mcap=self.max_mcap
        )
        
        return universe
    
    def _load_fmp_universe(self):
        """Load universe from FMP cached data."""
        print("\nLoading universe from FMP cache...")
        
        try:
            from fmp_provider import SmartDataManager
        except ImportError:
            print("ERROR: fmp_provider.py not found")
            print("Make sure fmp_provider.py is in the same directory")
            raise
        
        # Initialize (uses cached data - no API calls)
        manager = SmartDataManager(api_key="placeholder", cache_file="universe_cache.csv")
        
        # Get screener universe (applies market cap filter)
        universe = manager.get_screener_universe(
            min_mcap=self.min_mcap,
            max_mcap=self.max_mcap
        )
        
        if len(universe) == 0:
            print("\nERROR: Cache is empty!")
            print("Run this first: python build_universe.py")
            raise ValueError("Empty cache - need to build universe first")
        
        return universe
    
    def _load_capiq_universe(self):
        """Load universe from S&P Capital IQ."""
        print("\nLoading universe from CapIQ...")
        print("NOTE: Requires CapIQ credentials")
        
        # This would use CapIQProvider with credentials
        # from data_ingestion import CapIQProvider
        # provider = CapIQProvider(username=USERNAME, password=PASSWORD)
        # universe = provider.get_universe(self.min_mcap, self.max_mcap)
        
        raise NotImplementedError("CapIQ integration requires credentials")
    
    def _load_bloomberg_universe(self):
        """Load universe from Bloomberg Terminal."""
        print("\nLoading universe from Bloomberg...")
        print("NOTE: Requires Bloomberg Terminal with API access")
        
        raise NotImplementedError("Bloomberg integration requires Terminal access")
    
    def _load_csv_universe(self):
        """Load pre-built universe from CSV file."""
        csv_path = self.output_dir / "universe.csv"
        
        if not csv_path.exists():
            raise FileNotFoundError(f"Universe CSV not found at {csv_path}")
        
        print(f"\nLoading universe from {csv_path}")
        universe = pd.read_csv(csv_path)
        
        # Apply market cap filter
        universe = universe[
            (universe['market_cap'] >= self.min_mcap) &
            (universe['market_cap'] <= self.max_mcap)
        ]
        
        return universe
    
    def _generate_outputs(self, results: dict):
        """Generate Excel output and summary reports."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Main Excel file with all sectors
        excel_path = self.output_dir / f"equity_screen_{timestamp}.xlsx"
        self._export_to_excel(results, excel_path)
        
        # 2. Summary CSV
        summary_path = self.output_dir / f"screening_summary_{timestamp}.csv"
        self._export_summary(results, summary_path)
        
        # 3. Individual sector CSVs (for easy filtering)
        for sector, df in results.items():
            sector_safe = sector.replace(" ", "_").replace("/", "_")
            csv_path = self.output_dir / f"{sector_safe}_{timestamp}.csv"
            df.to_csv(csv_path, index=False)
            
        if self.google_folder_id:
            try:
                self._export_to_google_sheet(results, self.google_folder_id, self.google_creds, timestamp)
            except Exception as e:
                print(f"\n✗ Error exporting to Google Sheets: {e}")
        
        print(f"\n✓ Outputs generated:")
        print(f"  Main file: {excel_path}")
        print(f"  Summary: {summary_path}")
    
    def _export_to_excel(self, results: dict, path: Path):
        """Export results to multi-sheet Excel file."""
        
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = []
            total_candidates = 0
            
            for sector in GICS_SECTORS:
                df = results.get(sector, pd.DataFrame())
                total_candidates += len(df)
                
                summary_data.append({
                    'Sector': sector,
                    'Candidates': len(df),
                    'Avg Market Cap ($B)': df['market_cap'].mean() / 1e9 if len(df) > 0 else 0,
                    'Min Market Cap ($B)': df['market_cap'].min() / 1e9 if len(df) > 0 else 0,
                    'Max Market Cap ($B)': df['market_cap'].max() / 1e9 if len(df) > 0 else 0
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Individual sector sheets
            for sector in GICS_SECTORS:
                df = results.get(sector, pd.DataFrame())
                if len(df) > 0:
                    # Truncate sheet name to 31 chars (Excel limit)
                    sheet_name = sector[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"\nScreening Results Summary:")
            print(f"  Total candidates across all sectors: {total_candidates}")
            print(f"  Target per sector: 10")
            print(f"  Sectors with candidates: {sum(1 for x in summary_data if x['Candidates'] > 0)}")
    
    def _export_summary(self, results: dict, path: Path):
        """Export summary statistics to CSV."""
        
        all_results = []
        for sector, df in results.items():
            for _, row in df.iterrows():
                all_results.append({
                    'Sector': sector,
                    **row.to_dict()
                })
        
        summary_df = pd.DataFrame(all_results)
        summary_df.to_csv(path, index=False)

    def _extract_folder_id(self, folder_input: str) -> str:
        """Extract folder ID from a potentially full Google Drive URL."""
        if not folder_input:
            return None
        
        folder_input = folder_input.strip()
            
        if "drive.google.com" in folder_input:
            import re
            # Match /folders/ID or ?id=ID. Handles various URL structures including /u/0/ etc.
            match = re.search(r'folders/([a-zA-Z0-9-_]{25,})', folder_input)
            if match:
                return match.group(1)
            
            match = re.search(r'id=([a-zA-Z0-9-_]{25,})', folder_input)
            if match:
                return match.group(1)
                
        # If it's just a string, return it (assuming it's already an ID)
        return folder_input


    def _export_to_google_sheet(self, results: dict, folder_id: str, creds_path: str, timestamp: str):
        """Export results to a Master Google Sheet inside the specified folder."""
        import time
        from datetime import date
        
        actual_folder_id = self._extract_folder_id(folder_id)
        
        if 'gspread' not in sys.modules:
            print("ERROR: gspread or gspread_dataframe not installed. Run: pip install gspread gspread-dataframe")
            return
            
        creds_file_path = Path(creds_path)
        if not creds_file_path.exists():
            print(f"ERROR: Credentials file '{creds_path}' not found!")
            return

        # Use OAuth flow with desktop app credentials
        auth_user_path = creds_file_path.parent / "authorized_user.json"
        
        try:
            gc = gspread.oauth(
                credentials_filename=str(creds_file_path),
                authorized_user_filename=str(auth_user_path)
            )
        except Exception as e:
            print(f"ERROR during authentication: {e}")
            return
            
        master_sheet_title = "Master Equity Screener"
        print(f"\nSearching for '{master_sheet_title}'...")
        
        sh = None
        try:
            # Search for existing Master sheet
            all_sheets = gc.openall()
            for sheet in all_sheets:
                if sheet.title == master_sheet_title:
                    sh = sheet
                    print(f"  ✓ Found existing Master sheet.")
                    break
        except Exception as e:
            print(f"  ⚠️ Error searching for sheets: {e}")

        # Create if not found
        is_new_sheet = False
        if sh is None:
            print(f"  Creating new Master sheet in folder {actual_folder_id}...")
            is_new_sheet = True
            try:
                sh = gc.create(master_sheet_title, folder_id=actual_folder_id)
            except Exception as e:
                print(f"  Warning: Creation with folder_id failed ({e}). Attempting fallback...")
                sh = gc.create(master_sheet_title)
                try:
                    # Move to folder logic
                    file_metadata = gc.get_file_drive_metadata(sh.id)
                    old_parents = ",".join(file_metadata.get('parents', []))
                    gc.request('patch', 
                        f"https://www.googleapis.com/drive/v3/files/{sh.id}?addParents={actual_folder_id}&removeParents={old_parents}&supportsAllDrives=true",
                        json={} # Add empty body for PATCH
                    )
                    print(f"  ✓ Successfully moved to target folder.")
                except Exception as move_e:
                    print(f"  ✗ Could not move to target folder: {move_e}")

        # 2. Tab Naming Logic
        today = date.today().strftime("%Y-%m-%d")
        tab_name = today
        existing_worksheets = [ws.title for ws in sh.worksheets()]
        
        counter = 1
        while tab_name in existing_worksheets:
            counter += 1
            tab_name = f"{today} Run {counter}"
            
        print(f"Creating new tab: '{tab_name}'...")
        
        # 3. Data Consolidation
        all_dfs = []
        for sector, df in results.items():
            if not df.empty:
                # Add sector column if not already present
                if 'sector' not in df.columns:
                    df = df.copy()
                    df.insert(0, 'sector', sector)
                all_dfs.append(df)
        
        if not all_dfs:
            print("  ⚠️ No data to upload.")
            return
            
        final_df = pd.concat(all_dfs, ignore_index=True)
        
        # 4. Upload Data
        try:
            num_rows = len(final_df) + 10
            num_cols = len(final_df.columns) + 2
            ws = sh.add_worksheet(title=tab_name, rows=str(num_rows), cols=str(num_cols))
            
            print(f"  Uploading {len(final_df)} records...")
            set_with_dataframe(ws, final_df)
            
            # 5. Premium Formatting
            print("  Applying premium formatting...")
            # Header range is 1st row, all columns
            from gspread.utils import rowcol_to_a1
            last_col_a1 = rowcol_to_a1(1, len(final_df.columns)).replace('1', '') # Get letter
            header_range = f"A1:{last_col_a1}1"
            
            ws.format(header_range, {
                "backgroundColor": {
                    "red": 0.1,   # 10%
                    "green": 0.3, # 30%
                    "blue": 0.4   # 40%
                },
                "horizontalAlignment": "CENTER",
                "textFormat": {
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                    "bold": True
                }
            })
            
            # Freeze the first row
            ws.freeze(rows=1)
            
            # 6. Cleanup
            if is_new_sheet:
                try:
                    sheet1 = sh.worksheet("Sheet1")
                    if not sheet1.get_all_values(): # If empty
                        sh.del_worksheet(sheet1)
                        print("  ✓ Deleted default 'Sheet1'.")
                except Exception:
                    pass # Sheet1 might already be gone or not exist
                    
            print(f"\n✓ Master Sheet '{master_sheet_title}' updated successfully!")
            print(f"  Tab: {tab_name}")
            print(f"  Link: {sh.url}")

        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                print(f"\n✗ API Rate limit hit. Please wait a few minutes and try again. Error: {e}")
            else:
                print(f"\n✗ Error during data transfer/formatting: {e}")
            raise # Re-raise to let main handle it if needed



# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='AI-Native Fundamental Equity Screening Agent'
    )
    
    parser.add_argument(
        '--data-source',
        choices=['yfinance', 'capiq', 'bloomberg', 'csv'],
        default='yfinance',
        help='Data source for universe and fundamentals'
    )
    
    parser.add_argument(
        '--output-dir',
        default='outputs/',
        help='Output directory for results'
    )
    
    parser.add_argument(
        '--min-mcap',
        type=float,
        default=1.0,
        help='Minimum market cap in billions'
    )
    
    parser.add_argument(
        '--max-mcap',
        type=float,
        default=50.0,
        help='Maximum market cap in billions'
    )
    
    parser.add_argument(
        '--google-folder-id',
        default='1B6shb7SZXVu6D-SPTyoUm9VJoFAkQmK3',
        help='Google Drive Folder ID to create new sheets inside'
    )
    
    parser.add_argument(
        '--google-creds',
        default='client_secret.json',
        help='Path to your Google OAuth client_secret.json'
    )
    
    args = parser.parse_args()
    
    # Initialize and run screener
    screener = ProductionScreener(
        data_source=args.data_source,
        output_dir=args.output_dir
    )
    
    screener.min_mcap = args.min_mcap * 1e9
    screener.max_mcap = args.max_mcap * 1e9
    screener.google_folder_id = args.google_folder_id
    screener.google_creds = args.google_creds
    
    try:
        results = screener.run_full_pipeline()
        print("\n✓ Screening completed successfully")
        return 0
    except Exception as e:
        print(f"\n✗ Error during screening: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
