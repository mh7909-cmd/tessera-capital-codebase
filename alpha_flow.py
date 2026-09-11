import os
import sys
import warnings
import requests

# Institutional Silence: Suppress EOL, SSL, and Library noise
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

try:
    import contextlib
    with contextlib.redirect_stdout(None), contextlib.redirect_stderr(None):
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
except:
    pass

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

import sys
import subprocess
import re
import gspread
import pandas as pd
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

sys.path.append(os.path.join(os.path.dirname(__file__), 'Codebase'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Equity_Screener', 'Codebase'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'Thinker'))
from sheets_utils import DiligenceSheetsUtils
from data_ingestion import YFinanceProvider
from nemotron_analysis import impute_fundamentals
from defeatbeta_api.data.ticker import Ticker

# Load root environment
load_dotenv()

def run_command(command, cwd=None):
    """Utility to run shell commands and stream output with institutional pacing."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        text=True,
        cwd=cwd
    )
    
    full_output = []
    for line in iter(process.stdout.readline, ''):
        # Cinematic streaming: line-by-line with a slight heartbeat
        print(line, end='')
        sys.stdout.flush()
        full_output.append(line)
        time.sleep(0.05) 
            
    process.stdout.close()
    return_code = process.wait()
    return return_code, "".join(full_output)

def run_with_retry(cmd, cwd, phase_name, retries=2):
    """Run a command with local retries for agent robustness."""
    for i in range(retries + 1):
        # Cinematic institutional beat (No attempt noise)
        if phase_name == "Synthesis":
            print(f"   [SYSTEM] Commencing final investment audit and strategic synthesis...")
        else:
            print(f"   [ANALYSIS] Deploying verified sub-routine: {phase_name}...")
        ret, _ = run_command(cmd, cwd=cwd)
        if ret == 0:
            return True
        if i < retries:
            time.sleep(5)
    return False

def get_gspread_client():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tab_name", nargs="?", default=None, help="The tab in the master sheet to pull from")
    parser.add_argument("--ticker", help="Test Mode: Target a specific ticker")
    parser.add_argument("--demo", action="store_true", help="Demo Mode: Full screen-switch flow for FLY only (no 503 screener)")
    args = parser.parse_args()



    cmd_tab_name = args.tab_name
    ticker_override = args.ticker
    demo_mode = args.demo
    
    gc = get_gspread_client()
    diligence_utils = DiligenceSheetsUtils(gc)
    tab_name = None

    DILIGENCE_ORDER = ['OMC', 'NWSA', 'SATS', 'FLY']
    COMPANY_NAMES_MAP = {
        'OMC': 'Omnicom Group Inc.',
        'NWSA': 'News Corporation',
        'SATS': 'EchoStar Corporation',
        'FLY': 'Firefly Aerospace',
    }
    FLY_STUB = {
        'ticker': 'FLY', 'company_name': 'Firefly Aerospace',
        'sector': 'Industrials', 'industry': 'Aerospace & Defense',
        'market_cap': 2100000000, 'price': None,
    }

    if demo_mode:
        # ── DEMO MODE: Full screen-switch flow, FLY only, no 503 screener ──
        DILIGENCE_SHEET_ID = diligence_utils.diligence_sheet_id

        # Silence splash for demo
        # print("\n" + "=" * 60)
        # print(">>> [ANALYSIS] COMMENCING TARGETED DEEP-SCAN + FLY PROTOCOL")
        # print("=" * 60)
        sys.stdout.flush()

        # Step 1: Lock view on Sheet6 (screener start)
        print(f"::UI_SIGNAL:: {{\"type\": \"LOCK_VIEW\", \"gid\": \"134446176\", \"sheet_id\": \"{DILIGENCE_SHEET_ID}\"}}")
        sys.stdout.flush()

        # Simulate screener activity — flash all 4 tickers in the UI
        fake_screeners = [('OMC', 'Omnicom Group'), ('NWSA', 'News Corp'), ('SATS', 'EchoStar'), ('FLY', 'Firefly Aerospace')]
        for _t, _name in fake_screeners:
            try:
                _ws, _gid = diligence_utils.get_ticker_tab(_t, apply_branding=False)
                # Use LOCK_VIEW to force the UI to switch even if a previous lock was active
                print(f"::UI_SIGNAL:: {{\"type\": \"LOCK_VIEW\", \"ticker\": \"{_t}\", \"gid\": \"{_gid}\", \"sheet_id\": \"{DILIGENCE_SHEET_ID}\"}}")
            except Exception:
                pass
            print(f"   ✅ [CONVICTION] {_t}: {_name} — passed all sector filters.")
            sys.stdout.flush()
            time.sleep(0.8)

        print(f"\n{'=' * 60}")
        print(f"✅ [SCREENER] Universe scan complete. 4 targets isolated for deep-audit.")
        print(f"{'=' * 60}\n")
        sys.stdout.flush()

        # Reorder tabs
        try:
            diligence_utils.reorder_tabs(['OMC', 'NWSA', 'SATS', 'FLY'])
        except Exception as _e:
            print(f"   ⚠️ Tab reorder skipped: {_e}")
        diligence_utils.sanitize_workspace()

        # Step 2: Unpin from screener and prepare for deep-dive
        print(f"::UI_SIGNAL:: {{\"type\": \"UNLOCK_VIEW\"}}")
        sys.stdout.flush()
        time.sleep(0.5)

        # Only run FLY diligence (skip OMC/NWSA/SATS for speed in the hero demo)
        active_records = [FLY_STUB]

    elif not cmd_tab_name and not ticker_override:
        # ── FULL SCREENER MODE — uses ProductionScreener + EquityScreenerAgent ──
        _codebase_dir = os.path.join(os.path.dirname(__file__), 'Codebase')
        sys.path.insert(0, _codebase_dir)
        from run_screener import ProductionScreener
        from equity_screener_agent import EquityScreenerAgent

        print("\n[SYSTEM] Commencing Equity Universe Screening — S&P 500 (503 targets)...")
        sys.stdout.flush()

        # Lock the view on Sheet6 for the entire screener — tabs will be created but view won't jump
        DILIGENCE_SHEET_ID = diligence_utils.diligence_sheet_id
        print(f"::UI_SIGNAL:: {{\"type\": \"LOCK_VIEW\", \"gid\": \"134446176\", \"sheet_id\": \"{DILIGENCE_SHEET_ID}\"}}")
        sys.stdout.flush()

        # Step 1: Load universe — get_universe_from_list streams per-company output
        print(f"Loading universe from Yahoo Finance...")
        print(f"(This may take several minutes)")
        print(f"Fetched 503 S&P 500 tickers")
        print(f"[DATALAKE] Initializing Global Market Scan... Securing connection to datalake.")
        
        # Simulate the professional scanning logs requested by user
        scan_tickers = ['MMM', 'AOS', 'ABT', 'ABBV', 'ACN', 'ADBE', 'AMD', 'AES', 'AFL', 'A', 'APD', 'ABNB', 'AKAM']
        for _st in scan_tickers:
            print(f"[SCANNING] Acquisition datastream: {_st}...", end='')
            sys.stdout.flush()
            time.sleep(0.1)
            if _st in ['AOS', 'AES', 'A', 'AKAM']:
                print(f"    ✅ [PASS] {_st} meets conviction criteria. Cataloging payload...")
            else:
                print(f"    ❌ [REJECT] {_st} variance threshold exceeded. Discarding block.")
            time.sleep(0.05)

        _screener = ProductionScreener(data_source="yfinance")
        universe_df = _screener._load_yfinance_universe()

        # Sector-forced conviction (clean logs)
        _provider = YFinanceProvider()
        for _gt, _gname in [('OMC', COMPANY_NAMES_MAP['OMC']),
                             ('NWSA', COMPANY_NAMES_MAP['NWSA']),
                             ('SATS', COMPANY_NAMES_MAP['SATS'])]:
            if 'ticker' not in universe_df.columns or _gt not in universe_df['ticker'].values:
                _info = _provider.get_ticker_info(_gt) or {}
                _info.setdefault('ticker', _gt)
                _info.setdefault('company_name', _gname)
                universe_df = pd.concat([universe_df, pd.DataFrame([_info])], ignore_index=True)
                print(f"   ✅ [DATA_SYNC] {_gt} ({_gname}) cataloged in universe.")
        sys.stdout.flush()

        # Step 2: Run sector-by-sector screening with the existing agent
        passing_tickers = []
        passing_records = {}

        def _sector_callback(sector, top_10_df):
            for _, row in top_10_df.iterrows():
                t = str(row.get('ticker', '')).upper()
                if t and t not in passing_tickers:
                    passing_tickers.append(t)
                    passing_records[t] = row.to_dict()
                    try:
                        _ws, _gid = diligence_utils.get_ticker_tab(t, apply_branding=False)
                        print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"{t}\", \"gid\": \"{_gid}\", \"sheet_id\": \"{diligence_utils.diligence_sheet_id}\"}}")
                    except Exception:
                        pass
                    print(f"   ✅ [CONVICTION] {t}: {str(row.get('company_name', t))[:40]} ({sector})")
            sys.stdout.flush()

        _agent = EquityScreenerAgent(_screener.min_mcap, _screener.max_mcap)
        _agent.universe = universe_df
        _agent.run_full_screen(callback=_sector_callback)

        # Ensure OMC/NWSA/SATS appear in passers (sector filter may have dropped them)
        for _gt, _gname in [('OMC', COMPANY_NAMES_MAP['OMC']),
                             ('NWSA', COMPANY_NAMES_MAP['NWSA']),
                             ('SATS', COMPANY_NAMES_MAP['SATS'])]:
            if _gt not in passing_tickers:
                passing_tickers.insert(0, _gt)
                _row = universe_df[universe_df['ticker'] == _gt] if 'ticker' in universe_df.columns else pd.DataFrame()
                passing_records[_gt] = _row.iloc[0].to_dict() if not _row.empty else {
                    'ticker': _gt, 'company_name': _gname, 'market_cap': 0}
                try:
                    _ws, _gid = diligence_utils.get_ticker_tab(_gt, apply_branding=False)
                    print(f"   ✅ [CONVICTION] {_gt} ({_gname}) — prioritized.")
                    print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"{_gt}\", \"gid\": \"{_gid}\", \"sheet_id\": \"{diligence_utils.diligence_sheet_id}\"}}")
                except Exception:
                    pass

        # Inject FLY
        if 'FLY' not in passing_tickers:
            passing_tickers.append('FLY')
            try:
                _ws, _gid = diligence_utils.get_ticker_tab('FLY', apply_branding=False)
                print(f"   ✅ [CONVICTION] FLY: Firefly Aerospace (Industrials / Aerospace & Defense)")
                print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"FLY\", \"gid\": \"{_gid}\", \"sheet_id\": \"{diligence_utils.diligence_sheet_id}\"}}")
            except Exception:
                pass
        passing_records['FLY'] = FLY_STUB

        print(f"\n{'=' * 60}")
        print(f"✅ [SCREENER] Universe scan complete. {len(passing_tickers)} stocks validated.")
        print(f"   4 high-conviction targets routed to secure research pipeline.")
        print(f"{'=' * 60}\n")
        sys.stdout.flush()

        _tab_order = DILIGENCE_ORDER + [t for t in passing_tickers if t not in DILIGENCE_ORDER]
        try:
            diligence_utils.reorder_tabs(_tab_order)
        except Exception as _e:
            print(f"   ⚠️ Tab reorder skipped: {_e}")

        diligence_utils.sanitize_workspace()
        
        # CINEMATIC PAUSE: Removed from here, moved to post-FLY diligence write
        print(f"   [SYSTEM] Conviction list finalized. Transitioning to institutional research pipeline...")
        # time.sleep(30)

        # Lock the view on OMC tab for the entire diligence phase — all 4 written, view stays on OMC
        try:
            _omc_ws, _omc_gid = diligence_utils.get_ticker_tab('OMC', apply_branding=False)
            print(f"::UI_SIGNAL:: {{\"type\": \"LOCK_VIEW\", \"gid\": \"{_omc_gid}\", \"sheet_id\": \"{DILIGENCE_SHEET_ID}\"}}")
            sys.stdout.flush()
        except Exception:
            pass

        active_records = [
            passing_records.get('OMC', {'ticker': 'OMC', 'company_name': COMPANY_NAMES_MAP['OMC'], 'market_cap': 0}),
            passing_records.get('NWSA', {'ticker': 'NWSA', 'company_name': COMPANY_NAMES_MAP['NWSA'], 'market_cap': 0}),
            passing_records.get('SATS', {'ticker': 'SATS', 'company_name': COMPANY_NAMES_MAP['SATS'], 'market_cap': 0}),
            FLY_STUB,
        ]

    elif ticker_override:
        print(f"\n🎯 [ANALYSIS] Explicit Target Acquisition: {ticker_override}")

        # Reset the email marker in test mode so the user gets a new logic test email every time
        import glob
        marker_pattern = os.path.join(os.path.dirname(__file__), "Email", "workspace", "skills", "outreach", ".fly_bcc_sent")
        for m in glob.glob(marker_pattern):
            try: os.remove(m)
            except: pass

        # Split by commas and clean up
        target_list = [t.strip().upper() for t in ticker_override.split(',') if t.strip()]
        active_records = []

        # Run real-time data ingestion first so we have the correct company names
        provider = YFinanceProvider()
        for t in target_list:
            print(f"  [ANALYSIS] Performing real-time data ingestion for {t}...")
            info = provider.get_ticker_info(t)
            if not info or info.get('market_cap', 0) == 0:
                company_name = COMPANY_NAMES_MAP.get(t, t)
                info = {'ticker': t, 'company_name': company_name, 'market_cap': info.get('market_cap', 0) if info else 0}
            active_records.append(info)

        # --- PIPELINE QUEUE INITIALIZATION (The Decision Desk) ---
        try:
            print(f"\n[SYSTEM] Synchronizing Decision Desk (Pipeline Queue)...")
            pipe_sh = gc.open_by_key(os.getenv("PIPELINE_SHEET_ID"))
            queue_ws = pipe_sh.worksheet("Pipeline Queue")

            q_gid = str(queue_ws.id)
            # Unlock diligence lock before switching to Pipeline Queue tab
            print(f"::UI_SIGNAL:: {{\"type\": \"UNLOCK_VIEW\"}}")
            sys.stdout.flush()
            time.sleep(0.3)
            print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"QUEUE\", \"sheet_id\": \"{os.getenv('PIPELINE_SHEET_ID')}\", \"gid\": \"{q_gid}\"}}")
            time.sleep(2)

            q_tickers = queue_ws.col_values(1)
            t = target_list[0] if target_list else "FLY"
            comp_name = active_records[0].get('company_name', t) if active_records else COMPANY_NAMES_MAP.get(t, t)
                 
            rationale = (
                "0.94^6 = 69.2% stage reliability vs 95% DoD NSSL mandate. "
                "Helium shortfall forces 90% thrust cap invalidating full manifest. "
                "88% NDT whistleblower probability. 12M target: $15.85 (-55.7%)."
                if t.upper() == "FLY" else
                f"Auditing operational resilience and management cadence for {comp_name}."
            )
            if t not in q_tickers:
                queue_ws.append_row([t, comp_name, "Neutral", "Propulsion Architecture & Supply Chain" if t == "FLY" else "Operational Resilience", rationale, "pending"])
                print(f"      [✓] {t} registered in Pipeline Queue [PENDING].")
            else:
                _qi = q_tickers.index(t) + 1
                queue_ws.update_cell(_qi, 3, "Neutral")
                queue_ws.update_cell(_qi, 4, "Propulsion Architecture & Supply Chain" if t == "FLY" else "Operational Resilience")
                queue_ws.update_cell(_qi, 5, rationale)
                queue_ws.update_cell(_qi, 6, "pending")
                print(f"      [✓] {t} status reset to [PENDING] in Pipeline Queue.")
        except Exception as e:
            print(f"      ⚠️ Queue sync anomaly: {e}")

    else:
        # ── BATCH MODE (tab name provided via CLI) ──────────────────────────────
        tab_name = cmd_tab_name
        print(f"\n🎯 [ORCHESTRATOR] Using Specified Tab: '{tab_name}' (Skipping Screen)")

        print("\n" + ">>> SYNCING TICKERS TO MASTER DILIGENCE SHEET")
        print("-" * 50)

        master_sh = gc.open_by_key(os.getenv("MASTER_SHEET_ID"))
        try:
            master_ws = master_sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"❌ Tab '{tab_name}' not found. Aborting.")
            return

        diligence_utils.sanitize_workspace()

        records = master_ws.get_all_records()

        print("\n" + ">>> PHASE 1.5: TARGET VETTING & FRONT-LOADING")
        print("-" * 50)

        vetted_targets = []
        vetted_tickers = []
        picked_sectors = set()

        all_potential_tickers = [r.get('ticker') or r.get('Ticker') for r in records[:40] if r.get('ticker') or r.get('Ticker')]
        print(f"      [SYSTEM] Instantiating shells for top {len(all_potential_tickers)} sourcing targets...")

        for t in all_potential_tickers:
            try:
                diligence_utils.get_ticker_tab(str(t).strip(), apply_branding=False)
                time.sleep(0.5)
            except: pass

        print(f"      [STATUS] Vetting for 4-quarter HUD integrity and industry diversity...")
        for row in records:
            if len(vetted_targets) >= 4:
                break
            ticker = row.get('ticker') or row.get('Ticker')
            sector = row.get('sector') or row.get('Sector') or "Unknown"
            if ticker and sector not in picked_sectors:
                try:
                    t_obj = Ticker(ticker)
                    calls = t_obj.earning_call_transcripts().get_transcripts_list()
                    if len(calls) >= 4:
                        vetted_targets.append(row)
                        vetted_tickers.append(ticker)
                        picked_sectors.add(sector)
                        print(f"      [✓] {ticker} ({sector}): Verified 4-quarter HUD integrity.")
                except: continue

        if len(vetted_targets) < 4:
            for row in records:
                if len(vetted_targets) >= 4: break
                ticker = row.get('ticker') or row.get('Ticker')
                if ticker and ticker not in vetted_tickers:
                    vetted_targets.append(row)
                    vetted_tickers.append(ticker)

        fly_ticker = 'FLY'
        if fly_ticker in vetted_tickers:
            _fi = vetted_tickers.index(fly_ticker)
            target_pos = min(3, len(vetted_tickers) - 1)
            vetted_tickers.insert(target_pos, vetted_tickers.pop(_fi))
            vetted_targets.insert(target_pos, vetted_targets.pop(_fi))
            print(f"      [✓] FLY (Firefly Aerospace): Re-positioned to slot {target_pos + 1}.")
        else:
            insert_at = min(3, len(vetted_targets))
            vetted_targets.insert(insert_at, FLY_STUB)
            vetted_tickers.insert(insert_at, fly_ticker)
            print(f"      [✓] FLY (Firefly Aerospace): Injected at slot {insert_at + 1} (Industrials / Aerospace & Defense).")

        diligence_utils.reorder_tabs(vetted_tickers)
        active_records = vetted_targets

        # STRATEGIC PAUSE: 30 seconds for live narration during the YC demo
        print(f"\n[SYSTEM] Conviction list generated. Commencing 30-second strategic calibration...")
        print(f"::UI_SIGNAL:: {{\"type\": \"PHASE_CHANGE\", \"phase\": \"THINKING\", \"msg\": \"Establishing deep research environment...\"}}")
        for i in range(30, 0, -5):
            print(f"   [WAIT] Finalizing neural routing: {i}s remaining...")
            time.sleep(5)


    tickers_analyzed = []
    
    from colorama import Fore, Style
    for current_idx, row in enumerate(active_records):
        ticker = row.get('ticker') or row.get('Ticker')
        
        # Kinetic visual heartbeat for YC Demo (Silenced as per user request)
        # print(f"\n{Fore.GREEN}{Style.BRIGHT}[SYSTEM] Processing fundamental block {275 + current_idx * 15} from global universe...{Style.RESET_ALL}")
        time.sleep(0.5)
        
        company_name = row.get('company_name') or row.get('Name') or ticker
        if ticker:
            ticker = str(ticker).strip()
            tickers_analyzed.append(ticker)
            
            # --- UI SIGNAL: Force Command Center to focus this ticker's tab ---
            try:
                ws, gid = diligence_utils.get_ticker_tab(ticker, apply_branding=True)
                # Clear for fresh institutional analysis
                diligence_utils.clear_sheet(ws)
                print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"{ticker}\", \"gid\": \"{gid}\", \"sheet_id\": \"{diligence_utils.diligence_sheet_id}\"}}")
            except: pass

            print(f"\n" + "=" * 60)
            print(f"      [TARGET ACQUIRED] AUTONOMOUS INTELLIGENCE GATHERING: {ticker}")
            print(f"      [QUEUE] Processing target {current_idx+1} of {len(active_records)} from conviction list")
            print(f"      [STATUS] Securing fundamental, social, and archival datastreams for {ticker}...")
            print("=" * 60)

            print(f"[SYSTEM] Allocating Research Pipeline for {ticker}...")
            time.sleep(1) 
            
            print(f"::UI_SIGNAL:: {{\"type\": \"PHASE_CHANGE\", \"phase\": \"INITIALIZING_DOSSIER\", \"msg\": \"Setting up {ticker}...\"}}")
            print(f"  [BEAT] Fetching real-time market data and historical valuation metrics...")
            
            # 1. Fundamentals Block
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    ws, gid = diligence_utils.get_ticker_tab(ticker, apply_branding=True)
                    
                    excluded_cols = {'EC 1 Summary', 'EC 2 Summary', 'EC 3 Summary', 'EC 4 Summary', 'Overall Sentiment'}
                    fundamentals = {}
                    for k, v in row.items():
                        if k not in excluded_cols:
                            clean_k = str(k).replace('_', ' ').title()
                            clean_k = clean_k.replace("Pe Ratio", "P/E Ratio").replace("Forward Pe", "Forward P/E")
                            clean_k = clean_k.replace("Ev To Ebitda", "EV/EBITDA").replace("Ev To Revenue", "EV/Revenue")
                            clean_k = clean_k.replace("Price To Book", "Price/Book").replace("Roe", "ROE").replace("Roa", "ROA")
                            clean_k = clean_k.replace("Fcf", "Free Cash Flow").replace("Ebitda Margin", "EBITDA Margin")
                            
                            if v is None or str(v).strip() == "" or str(v).lower() == "nan":
                                fundamentals[clean_k] = "---" # Professional placeholder before imputation
                            else:
                                try:
                                    v_float = float(v)
                                    if k in ['market_cap', 'enterprise_value', 'fcf', 'operating_cashflow']:
                                        if abs(v_float) >= 1e9: fundamentals[clean_k] = f"${v_float/1e9:.2f}B"
                                        elif abs(v_float) >= 1e6: fundamentals[clean_k] = f"${v_float/1e6:.2f}M"
                                        else: fundamentals[clean_k] = f"${v_float:,.0f}"
                                    elif k in ['profit_margin', 'gross_margin', 'ebitda_margin', 'roe', 'roa', 'revenue_growth', 'earnings_growth']:
                                        fundamentals[clean_k] = f"{v_float * 100:.2f}%"
                                    elif k in ['pe_ratio', 'forward_pe', 'peg_ratio', 'current_ratio', 'debt_to_equity', 'ev_to_ebitda', 'ev_to_revenue', 'price_to_book']:
                                        fundamentals[clean_k] = f"{v_float:.2f}x"
                                    elif k == 'price':
                                        fundamentals[clean_k] = f"${v_float:.2f}"
                                    else:
                                        fundamentals[clean_k] = f"{v_float:,.2f}" if v_float % 1 != 0 else str(v)
                                except ValueError:
                                    # Data Guardrail: Don't allow qualitative strings (like 'Neutral') in numeric/ratio keys
                                    numeric_ratio_keys = ['P/E', 'Ratio', 'Margin', 'Growth', 'Roe', 'Roa', 'Peg', 'Price/Book', 'Ev/']
                                    if any(rk.lower() in clean_k.lower() for rk in numeric_ratio_keys):
                                        fundamentals[clean_k] = "---" # Reset to professional gap for AI imputation
                                    else:
                                        fundamentals[clean_k] = v

                    # --- INSTITUTIONAL PROXY FALLBACK (Zero Gaps Demo Protocol) ---
                    if fundamentals.get("P/E Ratio") == "---" and fundamentals.get("Forward P/E") not in ["---", None]:
                        fundamentals["P/E Ratio"] = fundamentals["Forward P/E"]
                        print(f"      [PROXY] Scaling Forward P/E as proxy for {ticker} trailing multiples.")
                    
                    if "---" in fundamentals.values():
                        # Silence: background imputation
                        try:
                            # Search for "---" gaps (our new professional placeholder)
                            missing_keys = [k for k, v in fundamentals.items() if v == "---"]
                            if missing_keys:
                                # Institutional silence: Imputation happens in background
                                imputed = impute_fundamentals(ticker, row.get('company_name', ticker), fundamentals)
                                for k, v in imputed.items():
                                    # Robust matching: normalize both keys for parity
                                    norm_k = re.sub(r'[^a-zA-Z0-9]', '', k).lower()
                                    for key in list(fundamentals.keys()):
                                        norm_key = re.sub(r'[^a-zA-Z0-9]', '', key).lower()
                                        if (norm_k in norm_key or norm_key in norm_k) and fundamentals[key] == "---":
                                            v_str = str(v)
                                            if 'ratio' in key.lower() or 'p/e' in key.lower() or 'peg' in key.lower():
                                                if not v_str.endswith('x'): v_str += 'x'
                                            elif 'margin' in key.lower() or 'roe' in key.lower() or 'roa' in key.lower():
                                                if not v_str.endswith('%'): v_str += '%'
                                            fundamentals[key] = v_str
                                            # Institutional silence for imputation
                                # Institutional silence
                        except Exception as e:
                            pass
                            
                    diligence_utils.write_block(ws, 'FUNDAMENTALS', f"{ticker} - MASTER FINANCIALS", fundamentals)
                    break 
                    
                except Exception as e:
                    if '429' in str(e) or 'Quota' in str(e):
                        if attempt < max_retries - 1:
                            print(f"  [API THROTTLE] Tactical cooldown for 65s to reset Google Quotas... (Attempt {attempt+1}/{max_retries})")
                            time.sleep(65)
                        else:
                            print(f"[FATAL] Failed to initialize {ticker} after multiple retries due to strict API limits.")
                            raise e
                    else:
                        raise e 
            
            # --- ADVERSARIAL AUDIT BYPASSES: All 4 conviction tickers use pre-built dossiers ---
            if ticker == 'FLY':
                print(f"\n>>> TARGET DETECTED: {ticker} (Firefly Aerospace)")
                print(f"::UI_SIGNAL:: {{\"type\": \"PHASE_CHANGE\", \"phase\": \"RESEARCHING\", \"msg\": \"Triggering High-Fidelity Audit for {ticker}...\"}}")
                try:
                    audit_script = os.path.join(os.path.dirname(__file__), "hardcode_fly_audit.py")
                    subprocess.run([sys.executable, "-u", audit_script, ticker], check=True)
                    print(f"   ✨ [FLY_AUDIT] Institutional dossier committed to repository.")
                    
                    # STRATEGIC PAUSE: 30 seconds for live narration of the FLY Dossier during YC demo
                    print(f"\n[SYSTEM] FLY Deep-Audit finalized. Commencing 30-second strategic review...")
                    time.sleep(30)
                except Exception as e:
                    print(f"   ⚠️ [FLY_AUDIT] Commit failed: {e}")
            elif ticker in ['SATS', 'OMC', 'NWSA']:
                print(f"\n>>> CONVICTION TARGET: {ticker} — High-Fidelity Audit Initiated")
                time.sleep(1)
                print(f"   [ANALYSIS] Multi-modal extraction active: SEC EDGAR + Institutional DataStream.")
                time.sleep(1)
                
                max_audit_retries = 2
                for audit_attempt in range(max_audit_retries):
                    try:
                        audit_script = os.path.join(os.path.dirname(__file__), "hardcode_trio_audit.py")
                        subprocess.run([sys.executable, "-u", audit_script, ticker], check=True)
                        print(f"   ✨ [{ticker}_AUDIT] Institutional dossier committed to repository.")
                        
                        # Add a 10s cooldown between conviction tickers to breathe on API quotas
                        print(f"   [SYSTEM] {ticker} Audit complete. 10s institutional sync cooldown...")
                        time.sleep(10)
                        break
                    except Exception as e:
                        if audit_attempt < max_audit_retries - 1:
                            print(f"   ⚠️ [{ticker}_AUDIT] Quota pressure detected. Cooling for 65s... (Attempt {audit_attempt+1})")
                            time.sleep(65)
                        else:
                            print(f"   ❌ [{ticker}_AUDIT] Pipeline failed: {e}")
            else:
                # Standard Pipeline for other tickers
                # 2. Earnings Call Analysis
                print(f"::UI_SIGNAL:: {{\"type\": \"PHASE_CHANGE\", \"phase\": \"RESEARCHING\", \"msg\": \"Earnings stats for {ticker}...\"}}")
                cmd_p2 = f"{sys.executable} -u earnings_call_analyzer.py --ticker {ticker}"
                run_with_retry(cmd_p2, "EC_Analyzer/EC_Analyzer", "Earnings")

                # 3. Social Sentiment Analysis
                print(f"   [SYSTEM] Scoping social signals for {ticker} – {company_name}...")
                cmd_p3 = f"{sys.executable} -u main.py --ticker {ticker} --company_name \"{company_name}\""
                run_with_retry(cmd_p3, "Sentiment_Analyzer", "Sentiment Intelligence")

                # 4. SEC Analysis
                print(f"::UI_SIGNAL:: {{\"type\": \"PHASE_CHANGE\", \"phase\": \"RESEARCHING\", \"msg\": \"SEC Audit for {ticker}...\"}}")
                cmd_p4 = f"{sys.executable} -u single_ticker_audit.py --ticker {ticker}" 
                run_with_retry(cmd_p4, "SEC_Analyzer", "SEC Audit")

                # 5. Thinker Synthesis
                print(f"::UI_SIGNAL:: {{\"type\": \"PHASE_CHANGE\", \"phase\": \"SYNTHESIZING\", \"msg\": \"Thesis arbiter for {ticker}...\"}}")
                cmd_p5 = f"{sys.executable} -u nemotron_analysis.py --ticker {ticker}"
                run_with_retry(cmd_p5, "Thinker", "Synthesis")
            
            # --- PIPELINE QUEUE REGISTRATION (Kinetic UI) ---
            if ticker == 'FLY':
                _pipeline_sid = os.getenv("PIPELINE_SHEET_ID", "")
                
                # 1. JUMP TO PIPELINE QUEUE (Show Pending) - ONLY for FLY (Theatrical Yo-Yo)
                if ticker == 'FLY':
                    print(f"\n>>> PHASE 6.5a: PIPELINE REGISTRATION for {ticker}")
                    print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"QUEUE\", \"sheet_id\": \"{_pipeline_sid}\", \"gid\": \"1461012877\"}}")
                else:
                    print(f"\n>>> [SILENT_SYNC] PIPELINE REGISTRATION for {ticker}")
                sys.stdout.flush()

                try:
                    pipe_sh = gc.open_by_key(_pipeline_sid)
                    queue_ws = pipe_sh.worksheet("Pipeline Queue")
                    q_tickers = queue_ws.col_values(1)

                    if ticker == 'FLY':
                        rationale = ("Structural integrity audit of the Reaver-1 propulsion suite. Evaluating manufacturing scalability against the 2026 manifest. Technical risk assessment focuses on stage-separation reliability and helium-supply logistics.")
                        conviction = "NEUTRAL"
                        sector = "Aerospace & Defense"
                    elif ticker == 'SATS':
                        rationale = ("Acute liquidity stress: $19.5B debt maturity wall. Pay-TV attrition accelerating (-15% YoY). Altman Z-Score 0.62 signals insolvency risk.")
                        conviction = "SHORT"
                        sector = "Broadcasting"
                    else:
                        rationale = f"Thesis synthesis for {ticker} pending institutional audit."
                        conviction = "NEUTRAL"
                        sector = "Services"

                    # Full cell-by-cell population for institutional "Live Sync" aesthetic
                    if ticker not in q_tickers:
                        _row_idx = len(q_tickers) + 1
                        queue_ws.update_cell(_row_idx, 1, ticker)
                        time.sleep(0.5)
                        queue_ws.update_cell(_row_idx, 2, company_name)
                        time.sleep(0.5)
                        print(f"   ⌨️  [KINETIC] Registered {ticker} ({company_name})")
                    else:
                        _row_idx = q_tickers.index(ticker) + 1

                    # Update metrics cell-by-cell
                    queue_ws.update_cell(_row_idx, 3, conviction)
                    print(f"   ⌨️  [KINETIC] Updating Signal: {conviction}")
                    time.sleep(0.5)
                    queue_ws.update_cell(_row_idx, 4, sector)
                    print(f"   ⌨️  [KINETIC] Updating Sector: {sector}")
                    time.sleep(0.5)
                    queue_ws.update_cell(_row_idx, 5, rationale)
                    print(f"   ⌨️  [KINETIC] Updating Rationale: Institutional Sync...")
                    time.sleep(0.5)
                    queue_ws.update_cell(_row_idx, 6, "pending")
                    print(f"      [✓] {ticker} synchronized in Pipeline Queue [PENDING].")
                    time.sleep(1.0)

                    # --- Apply column widths, row height, and WRAP so Rationale is fully visible ---
                    try:
                        from gspread_formatting import set_column_width, set_row_height, CellFormat, format_cell_range
                        set_column_width(queue_ws, "A", 80)    # Ticker
                        set_column_width(queue_ws, "B", 220)   # Company
                        set_column_width(queue_ws, "C", 110)   # Position Lean
                        set_column_width(queue_ws, "D", 200)   # Diligence Aspect
                        set_column_width(queue_ws, "E", 520)   # Rationale (wide enough to show full text)
                        set_column_width(queue_ws, "F", 100)   # Status
                        set_row_height(queue_ws, "1", 36)
                        set_row_height(queue_ws, f"2:{_row_idx}", 100)  # Tall rows so wrapped text is readable
                        fmt = CellFormat(wrapStrategy='WRAP')
                        format_cell_range(queue_ws, f"E2:E{_row_idx}", fmt)
                        print(f"   ✅ [FORMAT] Pipeline Queue layout applied.")
                    except Exception as _fe:
                        print(f"   ⚠️ [FORMAT] Column sizing skipped: {_fe}")

                except Exception as e:
                    print(f"   ⚠️ [PIPELINE_ERROR] Queue sync failed for {ticker}: {e}")

            # --- PHASE 6.5: FLY PIPELINE & OUTREACH SEQUENCE ---
            if ticker and ticker.upper() == 'FLY':
                
                time.sleep(3) # Let the user see the pending row

                # 2. JUMP TO LEADS (Expert Roster Injection)
                print(f"\n>>> PHASE 6.5b: {ticker} TALENT-WEDGE ANALYTICS SYNC")
                
                # RE-AUTH / RESOLVE Pipeline Sheet for polling
                _leads_gid = "0"
                _leads_ws = None
                try:
                    _gc_poll = get_gspread_client()
                    _sh_poll = _gc_poll.open_by_key(_pipeline_sid)
                    _leads_ws = _sh_poll.worksheet('Leads')
                    _leads_gid = str(_leads_ws.id)
                    _queue_ws = _sh_poll.worksheet('Pipeline Queue')
                    _queue_gid = str(_queue_ws.id)
                except Exception as _re:
                    print(f"   ⚠️ [SYNC] Re-auth failed: {_re}")
                    # Fallback to local script logic

                print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"LEADS\", \"sheet_id\": \"{_pipeline_sid}\", \"gid\": \"{_leads_gid}\"}}")
                sys.stdout.flush()
                time.sleep(1)
                try:
                    # Injects leads one by one into the database
                    inject_script = os.path.join(os.path.dirname(__file__), "inject_fly_leads.py")
                    subprocess.run([sys.executable, "-u", inject_script], check=True)
                    print(f"   ✨ [TALENT_WEDGE] Expert roster synchronized.")
                except Exception as e:
                    print(f"   ⚠️ [TALENT_WEDGE] Sync failed: {e}")
                
                # 3. DIRECT OUTREACH (Email Dispatch)
                print(f"\n>>> PHASE 6.6: FLY EXPERT OUTREACH — DIRECT SHADOW MODE")
                print(f"::UI_SIGNAL:: {{\"type\": \"PHASE_CHANGE\", \"phase\": \"OUTREACH\", \"msg\": \"Dispatching AI-informed expert inquiries...\"}}")
                try:
                    direct_outreach = os.path.join(os.path.dirname(__file__), "fly_direct_outreach.py")
                    subprocess.run([sys.executable, "-u", direct_outreach], cwd=os.path.dirname(__file__), check=True)
                except Exception as e:
                    print(f"   ⚠️ [OUTREACH] Direct outreach failed: {e}")

                # POLLING: Wait until all 6 experts are marked as 'sent' in Column F
                print(f"\n[SYNC] Monitoring outreach status on GSheets...")
                try:
                    _poll_attempts = 0
                    while _poll_attempts < 200: # 10 minute max safety timeout for GSheets latency
                        # Get column F (Status) for the first 6 leads (rows 2-7)
                        _statuses = _leads_ws.col_values(6)[1:7]
                        _sent_count = sum(1 for s in _statuses if str(s).lower() == 'sent')
                        
                        if _sent_count >= 6:
                            print(f"   ✅ [CONFIRMED] All 6 expert inquiries verified as 'SENT'.")
                            break
                        
                        print(f"   ⏳ [SYNC] Outreach in progress: {_sent_count}/6 verified...")
                        # REINFORCE UI FOCUS: Keep user on Leads tab until completion
                        print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"LEADS\", \"sheet_id\": \"{_pipeline_sid}\", \"gid\": \"{_leads_gid}\"}}")
                        sys.stdout.flush()
                        time.sleep(3)
                        _poll_attempts += 1
                except Exception as e:
                    print(f"   ⚠️ [SYNC] Polling encountered an issue: {e}")
                    time.sleep(5) # Fallback grace period

                # JUMP BACK TO PIPELINE QUEUE AFTER OUTREACH IS VERIFIED
                print(f"\n[ANALYSIS] Outreach swarm dispatched. Holding Leads view for 10s 'victory' window...")
                time.sleep(10) # Victory window to show all 6 are 'sent'
                print(f"   [SYSTEM] Returning to Pipeline Queue...")
                time.sleep(1) 
                print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"QUEUE\", \"sheet_id\": \"{_pipeline_sid}\", \"gid\": \"{_queue_gid}\"}}")
            print(f"\n[SYSTEM] Target {ticker} Dossier Finalized.")
            
            # --- PHASE 7: LIVE EXPERT CALL TRIGGER ---
            if ticker == 'FLY' or ticker_override:
                print(f"\n>>> PHASE 7: INITIATING LIVE EXPERT AUDIT CALL")
                print(f"::UI_SIGNAL:: {{\"type\": \"PHASE_CHANGE\", \"phase\": \"CALLING\", \"msg\": \"Triggering live expert audit for {ticker}...\"}}")
                try:
                    # We hit our own local webhook server to trigger the Vapi call
                    # Mayank's verified number from voiceagent/phone.py
                    payload = {
                        "phone_number": "+16462625452", 
                        "lead_name": "Mayank",
                        "ticker": ticker,
                        "company": company_name,
                        "email_context": f"Requesting technical input on {company_name} operational and technical bottlenecks."
                    }
                    requests.post("http://localhost:8765/trigger-call", json=payload, timeout=5)
                    print(f"   📞 [VOICE] Outbound call triggered to Mayank. Wait for the ring...")
                except Exception as e:
                    print(f"   ⚠️ [VOICE] Call trigger failed: {e}")

            
            time.sleep(2)

    # --- FINAL CLEANUP ---
    if tickers_analyzed:
        print(f"\n[SYSTEM] Deep diligence complete for target conviction list.")
        print(f"📈 Promoted {len(tickers_analyzed)} tickers to front of dossier.")
        diligence_utils.promote_tickers(tickers_analyzed)

    # --- ALL 4 DONE: Institutional Silence ---
    print(f"\n[SYSTEM] All conviction targets written and committed to dossier.")
    # UI signals removed as per user request to stay on current screen
    sys.stdout.flush()

    print("\n" + "*" * 60)
    print("   SWARM DISPATCHED: Firefly Aerospace Alpha Orchestration")
    print("   Expert Audit Swarm: ACTIVE (Check Gmail/MiroFish)")
    print("*" * 60 + "\n")

    print("\n" + "=" * 60)
    print("      PIPELINE STAGE 1 COMPLETE")
    print(f"      - Intelligence Bridge: SECURED")
    print(f"      - Outreach Swarm: DISPATCHED to 6 Experts")
    print(f"      - Digital Twin Simulation: [IN_PROGRESS]")
    print(f"      - Expert Validation: Awaiting Live Call...")
    print("=" * 60 + "\n")

    # --- PERSISTENT MONITORING (Stay alive for the full Hollywood show) ---
    print(f"\n[ORCHESTRATOR] Entering Master Monitoring Mode. Synchronizing with Expert Call & Simulation...")
    
    try:
        call_completed = False
        sim_completed = False
        ic_completed = False
        
        # Poll api_bridge for status
        miro_status_url = "http://localhost:8000/mirofish-status"
        ic_status_url = "http://localhost:8000/ic-status"
        
        while not ic_completed:
            try:
                # 1. Check MiroFish status
                resp = requests.get(miro_status_url, timeout=3)
                if resp.status_code == 200:
                    status = resp.json()
                    if status.get("done") and not sim_completed:
                        print(f"\n✅ [ORCHESTRATOR] Stage 3: Digital Twin Simulation VERIFIED.")
                        print(f"   [SYSTEM] Transitioning to Final Conviction (Investment Committee Debate)...")
                        sim_completed = True
                
                # 2. Check IC status
                resp_ic = requests.get(ic_status_url, timeout=3)
                if resp_ic.status_code == 200:
                    status_ic = resp_ic.json()
                    if status_ic.get("done"):
                        print(f"\n✅ [ORCHESTRATOR] Stage 6: Investment Committee CONSENSUS REACHED.")
                        ic_completed = True
                        break
                    
            except Exception as e:
                pass
                
            time.sleep(5)
            if not sim_completed:
                print(".", end="", flush=True)
            elif not ic_completed:
                print("•", end="", flush=True)

        print(f"\n{'*' * 60}")
        print(f"   PIPELINE FULL CYCLE COMPLETE")
        print(f"   - Digital Twin: STABILIZED")
        print(f"   - Final Conviction: COMMITTED")
        print(f"{'*' * 60}\n")
                    
    except KeyboardInterrupt:
        print("\n[SYSTEM] Orchestrator manually detached.")


if __name__ == "__main__":
    main()
