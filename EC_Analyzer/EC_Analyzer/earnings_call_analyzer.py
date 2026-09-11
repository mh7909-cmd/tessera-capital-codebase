import os
import sys
import logging
import argparse

# Silence technical loggers for institutional-grade console output
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Ensure UTF-8 for Windows terminal output
if os.name == 'nt':
    os.environ["PYTHONUTF8"] = "1"
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

import time
import asyncio
import random
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from openai import AsyncOpenAI
from defeatbeta_api.data.ticker import Ticker

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

# --- Windows Compatibility Patch for defeatbeta-api ---
try:
    from defeatbeta_api.client.duckdb_conf import Configuration
    from defeatbeta_api.client.duckdb_client import DuckDBClient
    
    def get_duckdb_settings_patched(self):
        return [
            "INSTALL httpfs;",
            "LOAD httpfs;",
            f"SET GLOBAL http_keep_alive = {self.http_keep_alive}",
            f"SET GLOBAL http_timeout = {self.http_timeout}",
            f"SET GLOBAL http_retries = {self.http_retries}",
            f"SET GLOBAL http_retry_backoff = {self.http_retry_backoff}",
            f"SET GLOBAL http_retry_wait_ms = {self.http_retry_wait_ms}",
            f"SET GLOBAL threads = {self.threads}",
            f"SET GLOBAL parquet_metadata_cache = {self.parquet_metadata_cache}",
        ]
    
    def validate_httpfs_cache_patched(self):
        self.logger.debug("Bypassing cache validation on Windows")

    Configuration.get_duckdb_settings = get_duckdb_settings_patched
    DuckDBClient._validate_httpfs_cache = validate_httpfs_cache_patched
except ImportError:
    pass
# ------------------------------------------------------

load_dotenv()

# Configuration
SOURCE_SHEET_ID = os.getenv("SOURCE_SHEET_ID", '1R7r1c_rO_-VAfmY_RsrwV1lrEE3q0LxPX-G4TNC4pME')
MASTER_SHEET_ID = os.getenv("MASTER_SHEET_ID")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "meta/llama-3.1-8b-instruct")

NUM_WORKERS = 2  # Reduced to prevent rate-limit cascade
API_SEMAPHORE = None  # Initialized in main() to limit concurrent API calls

TARGET_COLUMNS = ["Ticker", "EC 1 Summary", "EC 2 Summary", "EC 3 Summary", "EC 4 Summary", "Overall Sentiment"]

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

async def backoff_request(func, *args, max_retries=7, initial_delay=5, **kwargs):
    """Retries a function with exponential backoff on 429 (Rate Limit) errors."""
    global API_SEMAPHORE
    sem = API_SEMAPHORE or asyncio.Semaphore(2)
    async with sem:
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "rate limit" in err_msg or "quota" in err_msg:
                    delay = initial_delay * (2 ** attempt) + random.uniform(1, 3)
                    # Silent retry for institutional stability
                    await asyncio.sleep(delay)
                else:
                    raise e
        raise Exception("Max retries exceeded for API request.")

async def fetch_api_transcripts(ticker_symbol, limit=4):
    """Uses defeatbeta-api to fetch available transcripts."""
    # Internal data acquisition
    try:
        ticker_obj = Ticker(ticker_symbol)
        transcripts_obj = ticker_obj.earning_call_transcripts()
        
        # Get list of transcripts and sort by date descending
        df_list = transcripts_obj.get_transcripts_list()
        if df_list is None or df_list.empty:
            return []
            
        df_list = df_list.sort_values(by='report_date', ascending=False).head(limit)
        
        full_texts = []
        for _, row in df_list.iterrows():
            year = int(row['fiscal_year'])
            quarter = int(row['fiscal_quarter'])
            
            try:
                # Fetch paragraph data and join content
                df_paragraphs = transcripts_obj.get_transcript(year, quarter)
                full_text = " ".join(df_paragraphs['content'].astype(str).tolist())
                # Limit to chars to manage token costs
                full_texts.append(full_text[:30000])
            except Exception as e:
                print(f"  [{ticker_symbol}] Warning: Failed to fetch Q{quarter} {year}: {e}")
                
        return full_texts
    except Exception as e:
        print(f"  [{ticker_symbol}] API Fetch failed: {e}")
        return []

async def analyze_stock_data(client, ticker, transcripts, worksheet, row_idx, headers):
    """Analyzes found transcripts and writes summaries to sheet in real-time."""
    summaries = []
    
    # Analyze each transcript
    for i, text in enumerate(transcripts):
        # Institutional analysis in progress
        prompt = f"Read the following transcript for {ticker} and provide a 200-300 word financial summary.\n\nFormat your output strictly as plain text. Do NOT use markdown. Do NOT use **bold** or italics formatting. No conversational preambles (e.g. 'Here is a summary...'). Start immediately with the first section header.\n\nRequired sections:\nMetrics:\nManagement Tone:\nGuidance:\nDrivers:\nRisks:\n\nTranscript:\n{text}"
        
        response = await backoff_request(
            client.chat.completions.create,
            model=LLM_MODEL,
            max_tokens=600,
            messages=[
                {"role": "system", "content": "You are an expert financial analyst. You must output perfectly flat plain text. NO conversational preamble and NO markdown formatting (e.g. asterisks)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        summary = response.choices[0].message.content
        summaries.append(summary)
        
        # Real-time writing
        summary_header = f"EC {i+1} Summary"
        if summary_header in headers:
            col_idx = headers.index(summary_header) + 1
            await backoff_request(worksheet.update_cell, row_idx, col_idx, summary)
            # Real-time synchronization
            await asyncio.sleep(0.5)

    # Final overall sentiment
    if summaries:
        # Sentiment synthesis
        overall_prompt = f"Based on these {len(summaries)} earnings call summaries for {ticker}, provide an overall sentiment (Bullish, Bearish, or Neutral) and a 1-2 sentence justification.\n\nYou must explicitly state the sentiment word ('Bullish', 'Bearish', or 'Neutral'), followed by your 1-2 sentence explanation on a new line.\n\nSummaries:\n" + "\n\n".join(summaries)
        
        overall = await backoff_request(
            client.chat.completions.create,
            model=LLM_MODEL,
            max_tokens=200,
            messages=[
                {"role": "system", "content": "You are an expert financial analyst. You must output perfectly flat plain text. State the rating, and explicitly provide the justification. NO markdown formatting."},
                {"role": "user", "content": overall_prompt}
            ],
            temperature=0.3
        )
        overall_sentiment = overall.choices[0].message.content
        if "Overall Sentiment" in headers:
            sentiment_col = headers.index("Overall Sentiment") + 1
            await backoff_request(worksheet.update_cell, row_idx, sentiment_col, overall_sentiment)
            # Final commitment
            
        return summaries, overall_sentiment
    return [], "No data available."

async def stock_worker(queue, client, worksheet, headers):
    """The main parallel worker that processes stocks from the queue."""
    while True:
        item = await queue.get()
        if item is None:
            break
        
        ticker, row_idx = item
        print(f"   ⌨️  [KINETIC] Synchronizing {ticker} Analysis...")
        
        try:
            # 1. Fetch Transcripts from API
            transcripts_content = await fetch_api_transcripts(ticker)
            
            if not transcripts_content:
                print(f"  [{ticker}] Skipping: No transcripts found via API.")
                queue.task_done()
                continue
            
            # 2. Analyze & Write in real time
            await analyze_stock_data(client, ticker, transcripts_content, worksheet, row_idx, headers)
            
            print(f"      [✓] {ticker} intelligence committed to institutional dossier.")
            
        except Exception as e:
            print(f"  [{ticker}] FATAL Error in worker: {e}")
            pass
        finally:
            queue.task_done()

def get_latest_worksheet(worksheets):
    """Finds the latest worksheet based on date parsing of the title."""
    latest_ws = None
    latest_date = None
    
    for ws in worksheets:
        title = ws.title.strip()
        if title.lower() in ('summary', 'master'):
            continue
            
        try:
            if date_parser:
                parsed_date = date_parser.parse(title)
            else:
                parsed_date = None
            
            if parsed_date:
                if latest_date is None or parsed_date > latest_date:
                    latest_date = parsed_date
                    latest_ws = ws
        except Exception:
            pass
            
    # Fallback if no dates were parsable
    if latest_ws is None and worksheets:
        valid = [w for w in worksheets if w.title.lower() not in ('summary', 'master')]
        if valid:
            latest_ws = valid[-1] # Usually the last one added
            
    return latest_ws

def extract_tickers_from_grid(grid):
    """Scans a 2D grid for 'Ticker' or 'Symbol' headers and extracts values below them."""
    tickers = set()
    for row_idx, row in enumerate(grid):
        for col_idx, cell in enumerate(row):
            if str(cell).strip().lower() in ('ticker', 'symbol'):
                # Found a header! Scan downwards in this column
                for scan_row in range(row_idx + 1, len(grid)):
                    val = str(grid[scan_row][col_idx]).strip()
                    if not val:
                        break # Stop at empty cell
                    if val.lower() in ('ticker', 'symbol', 'company'):
                        break # Stop at another header
                    tickers.add(val)
    return list(tickers)

async def main():
    global API_SEMAPHORE
    API_SEMAPHORE = asyncio.Semaphore(2)  # Max 2 concurrent API calls globally
    
    parser = argparse.ArgumentParser(description="Institutional Earnings Call Analyzer")
    parser.add_argument("--tab", help="Specific worksheet name to process")
    parser.add_argument("--ticker", help="Specific ticker to process (overrides sheet scan)")
    args = parser.parse_args()

    if not NVIDIA_API_KEY:
        print("CRITICAL: NVIDIA API Key is missing in .env")
        return

    target_tab_name = args.tab
    target_ticker = args.ticker

    print(f"--- Starting Earnings Call Analyzer with {LLM_MODEL} (2 workers) ---")

    
    # Auth
    cred_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
    
    try:
        # Check local and root
        if not os.path.exists(cred_file):
            root_creds = os.path.join("..", "..", cred_file)
            if os.path.exists(root_creds):
                cred_file = root_creds

        if not os.path.exists(cred_file):
            print(f"CRITICAL: Google Credentials file '{cred_file}' NOT FOUND.")
            return

        creds = Credentials.from_service_account_file(cred_file, scopes=SCOPES)
        gc = gspread.authorize(creds)
        print(f"Connecting to Google Sheet as: {creds.service_account_email}")

        
    except Exception as e:
        print(f"CRITICAL: Google Auth failed: {e}")
        return

    # Open target sheet
    if not MASTER_SHEET_ID or MASTER_SHEET_ID == "your_master_sheet_id_here":
        print("CRITICAL: MASTER_SHEET_ID is not configured in .env!")
        return
        
    try:
        sheet = gc.open_by_key(MASTER_SHEET_ID)
        print(f"Successfully opened sheet: {sheet.title}")
    except Exception as e:
        print(f"CRITICAL: Failed to open sheet ({MASTER_SHEET_ID}): {e}")
        return
    
    client = AsyncOpenAI(
        base_url=NVIDIA_BASE_URL,
        api_key=NVIDIA_API_KEY
    )
    
    if target_tab_name:
        try:
            latest_ws = sheet.worksheet(target_tab_name)
            print(f"✅ Using specified tab: '{target_tab_name}'")
        except gspread.exceptions.WorksheetNotFound:
            print(f"❌ Target tab '{target_tab_name}' not found. Falling back to latest.")
            latest_ws = get_latest_worksheet(sheet.worksheets())
    else:
        latest_ws = get_latest_worksheet(sheet.worksheets())
    
    if not latest_ws:
        print("CRITICAL: Could not identify a valid latest data tab.")
        return
        
    print(f"\n[TAB] Identifying tickers in the tab: {latest_ws.title}...")
    
    try:
        data = latest_ws.get_all_records()
    except Exception as e:
        print(f"  Error reading worksheet {latest_ws.title}: {e}")
        return

    if not data:
        print("No data found in the tab.")
        return

    headers = latest_ws.row_values(1)
    
    # Ensure our target columns exist in the tab
    # Note: we use TARGET_COLUMNS starting from index 1 since TARGET_COLUMNS[0] is 'Ticker'
    metrics_columns = ["EC 1 Summary", "EC 2 Summary", "EC 3 Summary", "EC 4 Summary", "Overall Sentiment"]
    for col in metrics_columns:
        if col not in headers:
            headers.append(col)
            try:
                latest_ws.update_cell(1, headers.index(col)+1, col)
            except Exception:
                latest_ws.add_cols(1)
                latest_ws.update_cell(1, headers.index(col)+1, col)
            time.sleep(1)

    # Fill queue
    queue = asyncio.Queue()
    for i, row in enumerate(data):
        ticker = row.get('ticker') or row.get('Ticker') or row.get('Symbol')
        if ticker:
            ticker = str(ticker).strip().upper()
            # If a specific ticker was requested via CLI, skip others
            if target_ticker and ticker != target_ticker.strip().upper():
                continue
            queue.put_nowait((ticker, i + 2))
    
    if queue.empty(): 
        print("No tickers found in the tab.")
        return
        
    # Format the entire sheet for text wrapping so the summaries are readable
    try:
        latest_ws.format("A1:Z1000", {
            "wrapStrategy": "WRAP",
            "verticalAlignment": "TOP"
        })
        print(f"  [FORMAT] Text-wrapping applied to {latest_ws.title}")
    except Exception as e:
        print(f"  Warning: Could not format sheet for wrapping: {e}")
        
    # Launch Workers
    print(f"--- Launching {NUM_WORKERS} workers for tab {latest_ws.title} ---")
    workers = [asyncio.create_task(stock_worker(queue, client, latest_ws, headers)) for _ in range(NUM_WORKERS)]
    
    await queue.join()
    
    # Stop workers
    for _ in range(NUM_WORKERS):
        queue.put_nowait(None)
    await asyncio.gather(*workers)
    
    print("\n--- Pipeline Complete ---")

if __name__ == "__main__":
    asyncio.run(main())

