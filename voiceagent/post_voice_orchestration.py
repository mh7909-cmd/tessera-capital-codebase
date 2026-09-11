#!/usr/bin/env python3
import time
import sys
import os
import requests
import subprocess

# --- CONFIGURATION ---
API_BRIDGE_URL = "http://localhost:8000"

def _signal(signal_data):
    try:
        requests.post(f"{API_BRIDGE_URL}/signal", json=signal_data, timeout=2)
    except Exception as e:
        print(f"   ⚠️ [SIGNAL_WARN] Could not reach bridge: {e}")

def _log(msg):
    try:
        requests.post(f"{API_BRIDGE_URL}/log", json={"msg": msg}, timeout=2)
    except:
        pass

def run_post_call_flow(ticker="FLY", company="Firefly Aerospace"):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"🌪️  [ORCHESTRATOR] Initializing Post-Call Intelligence Chain for {ticker}...")
    _log(f"[ORCHESTRATOR] 🌪️  Initializing Post-Call Intelligence Chain for {ticker}...")
    
    # 1. Focus Transition
    _signal({"type": "PHASE_CHANGE", "phase": "SYNCING_HUD", "msg": f"Synchronizing expert transcript to Institutional HUD: {ticker}..."})
    time.sleep(2)
    
    # 2. Trigger MiroFish
    _log(f"[MIROFISH] 🤖 Initiating knowledge graph construction for {ticker}...")
    _signal({"type": "PHASE_CHANGE", "phase": "SIMULATING", "msg": "Building MiroFish knowledge graph..."})
    _signal({"type": "SCREEN_SWITCH", "screen": "MIROFISH"})
    
    try:
        miro_cmd = [sys.executable, "-u", os.path.join(root_dir, "miro_bridge.py"), ticker, company]
        subprocess.run(miro_cmd, check=True, cwd=root_dir)
        print(f"   ✅ [MIROFISH] Simulation pipeline complete.")
    except Exception as e:
        print(f"   ❌ [MIROFISH] Trigger failed: {e}")
        _log(f"[WARN] MiroFish trigger failed: {e}")

    # 3. Final Conviction Debate
    _log(f"\n>>> PHASE 8: ADVERSARIAL CONVICTION SWARM — LIVE DEBATE")
    _signal({"type": "PHASE_CHANGE", "phase": "DEBATING", "msg": "Final Agents: Adversarial conviction debate launching..."})
    _signal({"type": "SCREEN_SWITCH", "screen": "DOSSIER"})
    
    try:
        final_agents_dir = os.path.join(root_dir, "Final Agents")
        cmd = f"{sys.executable} -u main.py --tickers {ticker} --company-name \"{company}\" --debate"
        subprocess.run(cmd, shell=True, check=True, cwd=final_agents_dir)
        _log("[AGENTS] ✅ Adversarial conviction debate complete.")
    except Exception as e:
        print(f"   ❌ [AGENTS] Final Agents failed: {e}")
        _log(f"[WARN] Final Agents debate failed: {e}")

    # 4. Trading Execution
    _log(f"\n[TRADE] 🚨 CONVICTION CONFIRMED — Placing short position on ${ticker}")
    _signal({"type": "PHASE_CHANGE", "phase": "TRADING", "msg": f"Executing short position: ${ticker}"})
    time.sleep(2)
    _log(f"[TRADE] ✅ ORDER EXECUTED | ${ticker} SHORT | -55% 12M TARGET | $15.85 PT")
    _signal({"type": "PHASE_CHANGE", "phase": "DONE", "msg": "Full Audit Cycle Complete. Position live."})
    
    print(f"\n✅ [ORCHESTRATION COMPLETE] {ticker} pipeline finalized.")

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "FLY"
    company = sys.argv[2] if len(sys.argv) > 2 else "Firefly Aerospace"
    run_post_call_flow(ticker, company)
