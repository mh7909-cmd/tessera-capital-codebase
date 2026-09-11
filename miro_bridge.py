#!/usr/bin/env python3
import os
import sys
import json
import time

# Add required paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, 'Codebase'))
sys.path.append(os.path.join(ROOT_DIR, 'MiroFish', 'backend'))

from dotenv import load_dotenv
load_dotenv()

import gspread
from google.oauth2.service_account import Credentials
from Codebase.sheets_utils import DiligenceSheetsUtils
from MiroFish.backend.app.services.autonomous_sim_service import AutonomousSimService

def trigger_miro_simulation(ticker, company_name, transcript_path=None):
    """
    1. Fetches research dossier from the Institutional HUD (GSheets).
    2. Consolidates into a resilient text format.
    3. Triggers Miro Fish Autonomous Pipeline (full graph build included).

    transcript_path: path to Vapi call transcript — logged for show, not fed into sim.
    """
    print(f"\n🚀 [MIRO BRIDGE] Initializing Resilience Simulation for {ticker}...")
    
    # Ingest transcript into dossier when provided (used below after GSheets fetch)
    _transcript_text = None
    if transcript_path and os.path.exists(transcript_path):
        size = os.path.getsize(transcript_path)
        print(f"   📞 [TRANSCRIPT] Expert call transcript received ({size} bytes). Appending to institutional dossier.")
        with open(transcript_path, "r") as _f:
            _transcript_text = _f.read()
    
    _creds_file = os.path.join(ROOT_DIR, "credentials.json")
    _scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    _creds = Credentials.from_service_account_file(_creds_file, scopes=_scopes)
    _gc = gspread.authorize(_creds)
    utils = DiligenceSheetsUtils(_gc)
    # 1. Fetch Qualitative HUD Data (Sheets)
    dossier_lines = [f"--- INSTITUTIONAL RESEARCH DOSSIER: {ticker} ({company_name}) ---"]
    try:
        if not utils.diligence_sheet_id:
            raise ValueError("DILIGENCE_SHEET_ID not found in environment.")
            
        sh = utils.gc.open_by_key(utils.diligence_sheet_id)
        ws = sh.worksheet(ticker)
        data = ws.get_all_values()
        
        for row in data:
            # Col A-B: Master Financials
            if len(row) >= 2 and row[0].strip():
                dossier_lines.append(f"{row[0]}: {row[1]}")
            # Col D-E: SEC Qualitative Health
            if len(row) >= 5 and row[3].strip():
                dossier_lines.append(f"{row[3]}: {row[4]}")
            # Col G-H: Earnings Call Intelligence, Social Media Signals, Strategic Synthesis
            if len(row) >= 8 and row[6].strip():
                dossier_lines.append(f"{row[6]}: {row[7]}")
        print(f"   📥 [SIGNAL] Ingested GSheets intelligence for {ticker}.")
    except Exception as e:
        print(f"   ⚠️ [SIGNAL_WARN] GSheets intelligence unavailable for {ticker} — using transcript only.")
        print(f"   [INFO] Proceeding with transcript and thread data only.")
        
    # 2. Fetch Primary Research Signals (Email / Call Threads)
    try:
        pipeline_id = os.environ.get("PIPELINE_SHEET_ID")
        if pipeline_id:
            pipeline_ws = utils.gc.open_by_key(pipeline_id).get_worksheet(0)
            all_threads = pipeline_ws.get_all_records()
            
            # Filter threads for this company
            company_threads = []
            for t in all_threads:
                if company_name.lower() in t.get('Company', '').lower() or ticker.lower() in t.get('Subject', '').lower():
                    history = t.get('Full_Thread_History', '').strip()
                    if history:
                        company_threads.append(f"RECIPIENT: {t.get('Recipient Name')}\nSUBJECT: {t.get('Subject')}\nTHREAD:\n{history}")
            
            if company_threads:
                dossier_lines.append("\n--- PRIMARY RESEARCH: EXPERT DIALOGUE & THREADS ---")
                dossier_lines.extend(company_threads)
                print(f"   📥 [SIGNAL] Ingested {len(company_threads)} outreach threads into dossier.")
    except Exception as e:
        print(f"   ⚠️ [SIGNAL_WARN] Failed to bridge email threads: {e}")

    # Append expert call transcript to dossier so MiroFish ingests it
    if _transcript_text:
        dossier_lines.append("\n--- EXPERT CALL TRANSCRIPT ---")
        dossier_lines.append(_transcript_text)

    dossier_text = "\n".join(dossier_lines)
    
    # 3. Finalize Dossier & Trigger Sim
    try:
        temp_dir = os.path.join(ROOT_DIR, 'MiroFish', 'tmp')
        os.makedirs(temp_dir, exist_ok=True)
        dossier_path = os.path.join(temp_dir, f"{ticker}_dossier.txt")
        
        with open(dossier_path, "w") as f:
            f.write(dossier_text)
            
        print(f"✅ [Dossier Created] {os.path.basename(dossier_path)}")

        # Trigger MiroFish
        print("🤖 [MiroFish] Starting Parallel Simulation (10 Rounds)...")
        service = AutonomousSimService()
        
        result = service.run_pipeline(
            file_path=dossier_path,
            requirement=f"Evaluate the management sentiment and operational resilience of {company_name} based on official transcripts and analyst notes.",
            rounds=10,
            project_name=f"Demo_Resilience_{ticker}"
        )
        
        if result.get("success"):
            print(f"✨ [SIMULATION COMPLETE] Report Generated: {result.get('report', {}).get('display_name')}")
            return result
        else:
            print(f"❌ [SIMULATION FAILED] {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ [BRIDGE ERROR] {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 2:
        t_path = sys.argv[3] if len(sys.argv) > 3 else None
        trigger_miro_simulation(sys.argv[1], sys.argv[2], transcript_path=t_path)
    else:
        print("Usage: python3 miro_bridge.py <TICKER> <COMPANY_NAME> [transcript_path]")
