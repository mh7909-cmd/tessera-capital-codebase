#!/usr/bin/env python3
import subprocess
import requests
import sys
import os
import json

API_BRIDGE_URL = "http://localhost:8000"

def _log(msg):
    try:
        requests.post(f"{API_BRIDGE_URL}/log", json={"msg": msg}, timeout=2)
    except:
        pass

def _signal(signal_type, data=None):
    try:
        payload = {"type": signal_type}
        if data:
            payload.update(data)
        requests.post(f"{API_BRIDGE_URL}/signal", json=payload, timeout=2)
    except:
        pass

def sanitize_dossier(input_path, output_path):
    """Aggressive Whitelist: Only keep high-value institutional data."""
    if not os.path.exists(input_path):
        return None
    
    with open(input_path, 'r') as f:
        content = f.read()
    
    # White-list of institutional headers we care about
    WHITELIST_HEADERS = [
        "--- INSTITUTIONAL RESEARCH DOSSIER",
        "FLY - MASTER FINANCIALS",
        "FLY - SEC QUALITATIVE HEALTH",
        "FLY - EARNINGS CALL INTELLIGENCE",
        "FLY - SOCIAL MEDIA SIGNALS",
        "--- EXPERT CALL TRANSCRIPT",
        "TECHNICAL AUDIT"
    ]
    
    lines = content.split('\n')
    clean_lines = []
    current_section_valid = False
    
    for line in lines:
        # Detect start of a valid section
        if any(h in line for h in WHITELIST_HEADERS):
            current_section_valid = True
            clean_lines.append(line)
            continue
            
        # Detect start of a forbidden section (Outreach Logs)
        if "FLY - OUTREACH LOGS" in line or "RESEARCH REQUESTS" in line:
            current_section_valid = False
            continue
            
        # If we are in a valid section and not an outreach JSON block
        if current_section_valid:
            # Drop JSON blocks (emails)
            if '"Sender":' in line or '"Recipient Name":' in line:
                continue
            # Keep the line if it's not a lonely bracket/comma from a stripped block
            if line.strip() not in ["{", "}", "},", "],", "["]:
                clean_lines.append(line)
                
    with open(output_path, 'w') as f:
        f.write("\n".join(clean_lines))
    return output_path

def run_final_agents(ticker="FLY", company_name="Firefly Aerospace"):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    agents_dir = os.path.join(root_dir, "Final Agents")
    dossier_path = os.path.join(root_dir, "MiroFish", "tmp", f"{ticker}_dossier.txt")
    
    _log(f"[SYSTEM] Initializing Final Adversarial Debate for {ticker}...")
    _signal("SCREEN_SWITCH", {"screen": "LEADS"})
    _signal("PHASE_CHANGE", {"phase": "DEBATING"})
    
    cmd = [
        sys.executable, "-u", "main.py",
        "--tickers", ticker,
        "--company-name", company_name,
        "--debate"
    ]
    
    clean_dossier_path = os.path.join(root_dir, "Final Agents", "dossier_clean.txt")
    
    if os.path.exists(dossier_path):
        _log(f"[SYSTEM] Sanitizing Dossier for {ticker}...")
        sanitized = sanitize_dossier(dossier_path, clean_dossier_path)
        cmd.extend(["--context-file", clean_dossier_path])
        _log(f"[SYSTEM] Context file cleaned. Focusing on Financials & Expert Transcripts.")
    else:
        _log(f"[SYSTEM] ⚠️ Warning: No pre-seeded dossier found at {dossier_path}. Running with live data only.")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=agents_dir,
        text=True,
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"}
    )

    import time
    agent_output_buffer = []
    in_agent_block = False
    
    for line in process.stdout:
        clean_line = line.strip()
        if not clean_line:
            continue
            
        print(clean_line)
        
        # UI Bridge Signaling with Pacing (Cinematic Cadence)
        if "analysis complete" in clean_line or "[AGENT" in clean_line:
            # Staggered one-by-one release for theatrical clarity
            time.sleep(3.0) 
            _log(f"[AGENTS] {clean_line}")
        elif "FINAL INVESTMENT VERDICT" in clean_line or "[TRADING]" in clean_line:
            time.sleep(4.0)
            _log(f"[AGENTS] {clean_line}")
        elif "-----------------------" in clean_line:
            # Skip divider lines to reduce clutter
            pass
        elif any(x in clean_line for x in ['"Sender":', '"Recipient":', '"Full_Thread_History":']):
            # HARD BLOCK: Stop emails from leaking into the UI bridge
            pass
        elif clean_line.startswith(("{", "}")):
            # HARD BLOCK: Stop JSON blocks from leaking into the UI bridge
            pass
        elif not any(x in clean_line for x in ["DEBUG", "INFO", "Fetching", "Gathering", "Analyzing", "Research"]):
            # Filter for high-value reasoning text with minor pacing
            time.sleep(0.1)
            _log(f"[AGENTS] {clean_line}")

    process.wait()
    _log("[SYSTEM] Final Agents execution complete.")
    _signal("PHASE_CHANGE", {"phase": "DONE"})

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "FLY"
    company = sys.argv[2] if len(sys.argv) > 2 else "Firefly Aerospace"
    run_final_agents(ticker, company)
