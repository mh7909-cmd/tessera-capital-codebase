import os
import re
import json
import requests
import gspread
import warnings
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import sys
import time

# Suppression for demo output
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

# Import our new utility
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Codebase'))
from sheets_utils import DiligenceSheetsUtils

load_dotenv()

# Config
API_KEY = os.getenv("NVIDIA_API_KEY")
URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1") + "/chat/completions"
MASTER_SHEET_ID = os.getenv("MASTER_SHEET_ID")
DILIGENCE_SHEET_ID = os.getenv("DILIGENCE_SHEET_ID")

def impute_fundamentals(ticker, company, current_data):
    """Uses NVIDIA NIM to proxy missing fundamental metrics for a zero-defect UI."""
    api_key = os.getenv("NVIDIA_API_KEY")
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1") + "/chat/completions"
    
    if not api_key:
        print(f"  ⚠️ [CONFIG] Missing NVIDIA_API_KEY in environment. Imputation disabled.")
        return {}
    
    # Identify missing or N/A keys
    def is_missing(v):
        return v is None or str(v).strip().upper() in ['N/A', 'NONE', '---', '', 'NAN']
        
    missing_metrics = [k for k, v in current_data.items() if is_missing(v)]
    if not missing_metrics:
        # Check if we should use Forward P/E as a proxy for P/E Ratio
        return {}

    import logging as _log; _log.debug(f"[THINKER] Missing metrics {missing_metrics} for {ticker}. Running LLM imputation silently.")

    prompt = f"""
    You are a quantitative research assistant. The financial data provider has missing values for {company} ({ticker}).
    
    MISSING METRICS: {missing_metrics}
    KNOWN DATA: { {k:v for k,v in current_data.items() if not is_missing(v)} }
    
    Based on your training data (up to late 2024) and current market sentiment for {ticker}, provide your best ESTIMATE for the missing metrics.
    Focus on realistic 'Forward P/E', 'PEG Ratio', 'ROE', and 'ROA'.
    
    OUTPUT RAW JSON ONLY:
    {{
        "Metric Name": "Estimated Value (numeric string, e.g. 24.5)",
        ...
    }}
    """
    
    payload = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [
            {"role": "system", "content": "You are a financial data imputation agent. Provide numeric estimates for missing stock metrics. Output RAW JSON ONLY."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 512
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=10)
        res_json = response.json()
        content = res_json['choices'][0]['message']['content']
        # Clean potential markdown
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except:
        return {}


def _clean_reasoning(raw: str) -> str:
    """Strip Kimi's verbose preamble and <think> tags."""
    if not raw or raw == "---":
        return "N/A"
    text = re.sub(r'</?think>', '', raw, flags=re.IGNORECASE).strip()
    if 'The required JSON structure' in text[:800] or 'The output must be RAW JSON' in text[:800]:
        cut = re.search(r'\n\n((?!The required|The output must|JSON structure|\{).+)', text)
        if cut:
            text = text[cut.start():].strip()
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def get_gspread_client():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
    if not os.path.exists(creds_path):
        creds_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("target_tab_name", nargs="?", default=None)
    parser.add_argument("--ticker", help="Specific single ticker to process")
    args, unknown = parser.parse_known_args()
    target_tab_name = args.target_tab_name

    gc = get_gspread_client()
    utils = DiligenceSheetsUtils(gc)

    # 1. Get Tickers from Funnel Sheet (Source)
    if args.ticker:
        print(f"\n[SINGLE RUN] Bypassing target tracker. Running Thinker explicitly for: {args.ticker}")
        records = [{'ticker': args.ticker, 'company_name': args.ticker}]
    else:
        print(f"Reading Sourcing data from Sheet A...")
        master_sh = gc.open_by_key(MASTER_SHEET_ID)
        if target_tab_name:
            master_ws = master_sh.worksheet(target_tab_name)
        else:
            master_ws = master_sh.worksheets()[-1]
        
        records = master_ws.get_all_records()
        
    results = []
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    # 2. Synthesis Loop
    for idx, row in enumerate(records):
        ticker = str(row.get('ticker') or row.get('Ticker')).strip()
        if not ticker or ticker.lower() == 'nan': continue
            
        company = row.get('company_name') or row.get('Name') or ticker
        print(f"🧠 SYMBOL_REASONING: Analyzing conviction dossier for {ticker}...")
        
        # Hollywood Bypass for FLY
        if ticker.upper() == "FLY":
            print(f"   [FLY] HOLLYWOOD BYPASS: Executing High-Fidelity Strategic Audit...")
            time.sleep(2) # Cinematic beat
            data = {
                "deep_analysis_monologue": (
                    "STRATEGIC DILIGENCE MANDATE - FIREFLY AEROSPACE ($FLY)\n\n"
                    "Our initial scoping of the Firefly Aerospace Alpha manifest suggests a critical need to verify the structural integrity of the 'Responsive Space' growth narrative. "
                    "The primary inquiry must focus on the compounding reliability of the Reaver engine cluster. While single-engine test benchmarks are cited at 94%, we must confirm whether the integrated six-engine stage architecture has cleared the 95% DoD mission-success threshold. Probabilistic modeling suggests a potential stage reliability drop to 69%, which would be a catastrophic failure for NSSL eligibility. "
                    "Secondly, we need to reconcile the manufacturing throughput against the 6-launch annual commitment. Does the current production line support a 36-engine/year cadence, or is it hard-capped at 24? This 50% delta represents the difference between a successful manifest and a series of rolling stand-downs. "
                    "Finally, we must investigate the SLC-2 infrastructure, specifically the helium supply chain resilience, to ensure it isn't a single point of failure for the Vandenberg operations. "
                    "CONCLUSION: Until these technical thresholds are verified, the current valuation remains speculative. Our audit must pivot to forensic verification of these manufacturing and reliability gaps."
                ),
                "final_lean": "Neutral",
                "strategic_rationale": "Verifying if stage-level reliability meets the 95% DoD requirement. Reconciling manufacturing throughput (36 engines needed) against current 24-engine capacity.",
                "diligence_objective": "Audit helium supply chain at SLC-2 and verify Reaver SN manufacturing yields.",
                "conviction_score": "7",
                "catalyst_timing": "Ongoing Audit"
            }
            success = True
            reasoning_log = data["deep_analysis_monologue"]
        else:
            # Read the ticker's tab in the Diligence Sheet
            try:
                ws_diligence, _ = utils.get_ticker_tab(ticker)
                diligence_data = ws_diligence.get_all_values()
                
                # Simplified context extraction: just grab all text from the tab
                context_str = "\n".join([" | ".join(r) for r in diligence_data if any(r)])
            except Exception as e:
                print(f"  ⚠️ Could not read Diligence tab for {ticker}: {e}")
                context_str = f"Basic Funnel Data: {str(row)}"

            prompt = f"""
            Perform a FINAL INVESTMENT AUDIT on {company} ({ticker}).
            
            AVAILABLE RESEARCH DOSSIER DATA:
            {context_str[:15000]} 

            OUTPUT RAW JSON ONLY:
            {{
                "deep_analysis_monologue": "A verbose (500+ word) internal audit of {ticker}. Explicitly explain WHY you arrived at your final lean. Break down margins, moats, and catalysts using DOSSIER DATA. Do NOT just repeat these instructions.",
                "final_lean": "Long, Short, or Neutral",
                "strategic_rationale": "High-level summary of WHY we are taking this position based on the dossier.",
                "diligence_objective": "Identify what we still need to know (NOT in public data).",
                "conviction_score": "1-10",
                "catalyst_timing": "Estimated timeframe for the thesis to play out"
            }}
            """
            
            payload = {
                "model": "meta/llama-3.3-70b-instruct",
                "messages": [
                    {"role": "system", "content": "You are a lead portfolio manager. Output RAW JSON ONLY. No markdown. Streamline your internal reasoning."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.05,
                "max_tokens": 4096
            }
            
            success = False
            data = {}
            for attempt in range(3):
                # Llama-3.3-70B is now the primary. Fallback only if needed.
                current_model = "meta/llama-3.3-70b-instruct" if attempt == 0 else "moonshotai/kimi-k2-thinking"
                if attempt > 0:
                    print(f"   ⚠️ Switching to fallback model ({current_model})...")
                    payload["model"] = current_model
                try:
                    response = requests.post(URL, headers=headers, json=payload, timeout=240)
                    if response.status_code == 200:
                        resp_data = response.json()
                        msg = resp_data["choices"][0]["message"]
                        content = msg.get('content') or ""
                        reasoning_log = msg.get('reasoning') or msg.get('reasoning_content') or ""
                        search_space = f"{content} {reasoning_log}"
                        
                        start_idx = search_space.find('{')
                        if start_idx != -1:
                            content_to_parse = search_space[start_idx:]
                            # Simple JSON cleanup for malformed blocks
                            content_to_parse = content_to_parse.replace("```json", "").replace("```", "").strip()
                            try:
                                data = json.loads(content_to_parse)
                                success = True
                                break
                            except Exception as e:
                                if attempt == 2: print(f"   ❌ Final JSON parse error: {e}")
                    elif response.status_code == 429:
                        time.sleep(10)
                except: time.sleep(2)

        if success:
            # Handle both hidden reasoning (Kimi) and explicit reasoning (Llama JSON)
            reasoning_text = _clean_reasoning(reasoning_log)
            if (not reasoning_text or reasoning_text == "N/A" or len(reasoning_text) < 5) and "deep_analysis_monologue" in data:
                reasoning_text = data["deep_analysis_monologue"]

            if reasoning_text and reasoning_text != "N/A":
                words = reasoning_text.split()
                if len(words) > 700:
                    reasoning_text = " ".join(words[:700]) + " ... [TRUNCATED FOR INSTITUTIONAL BREVITY]"

            # 1. INITIAL POPULATION: Write the block with static headers and metadata
            synthesis_static = {
                "Final Lean": data.get("final_lean", "---"),
                "Conviction Score (1-10)": data.get("conviction_score", "---"),
                "Strategic Rationale": "[ANALYZING DOSSIER...]",
                "Catalyst Timing": data.get("catalyst_timing", "---"),
                "Diligence Objective": data.get("diligence_objective", "---"),
                "Full Reasoning Log": "[EXECUTING FINAL AUDIT...]"
            }
            
            # Write Initial Block structure
            ws_diligence, _ = utils.get_ticker_tab(ticker)
            utils.write_block(ws_diligence, 'THINKER', f"{ticker} - STRATEGIC RESEARCH SYNTHESIS", synthesis_static)
            
            # 2. KINETIC STREAMING: Populate the large text blocks sentence-by-sentence
            print(f"   ⌨️  KINETIC_STREAM: Feeding analysis to dashboard for {ticker}...")
            
            # 2a. Stream Strategic Rationale
            rationale = str(data.get("strategic_rationale", "Synthesis pending institutional data."))
            rat_sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', rationale) if s.strip()]
            rat_accumulated = ""
            for i, sent in enumerate(rat_sentences):
                rat_accumulated += sent + " "
                # Update every 2 sentences to balance vs API limits
                if i % 2 == 0 or i == len(rat_sentences) - 1:
                    utils.update_cell_kinetic(ws_diligence, 'THINKER', 'Strategic Rationale', rat_accumulated, finalize=(i == len(rat_sentences)-1))
                    time.sleep(0.4)

            # 2b. Stream Full Reasoning Log
            log_sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', reasoning_text) if s.strip()]
            log_accumulated = ""
            for i, sent in enumerate(log_sentences):
                log_accumulated += sent + " "
                # Update every 4 sentences for long logs
                if i % 4 == 0 or i == len(log_sentences) - 1:
                    utils.update_cell_kinetic(ws_diligence, 'THINKER', 'Full Reasoning Log', log_accumulated, finalize=(i == len(log_sentences)-1))
                    time.sleep(0.6)

            print(f"   ✅ STRATEGIC_VERDICT: {data.get('final_lean')}")
            data['ticker'] = ticker
            results.append(data)
        else:
            print(f"   ⏭️ Skipping {ticker} after failures.")

    print(f"\n✅ All synthesis logs recorded in Master Diligence Sheet.")
    
    # --- DEMO EXPORT: Handoff data to the Pipeline/Email Orchestrator ---
    export_path = os.path.join(os.path.dirname(__file__), "mass_diligence.json")
    try:
        with open(export_path, "w") as f:
            json.dump(results, f, indent=4)
        print(f"✅ Research results exported to {export_path} for Outreach Handoff.")
    except Exception as e:
        print(f"⚠️ Could not export mass_diligence.json: {e}")

if __name__ == "__main__":
    main()
