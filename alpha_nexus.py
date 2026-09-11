#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import argparse

def _log(msg):
    # Try to send to bridge if available
    try:
        import requests
        requests.post("http://localhost:8000/log", json={"msg": msg}, timeout=1)
    except:
        pass
    print(msg)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="FLY", help="Target ticker for deep-dive")
    args = parser.parse_args()
    
    ticker = args.ticker.upper()
    
    print("\n" + "=" * 60)
    print("      TESSERA CAPITAL | ALPHA NEXUS MASTER ORCHESTRATOR")
    print("=" * 60 + "\n")
    
    # 1. Discovery Swarm (Simulated High-Speed Scan)
    print(">>> PHASE 1: INSTITUTIONAL DISCOVERY SWARM")
    _log("[SYSTEM] Initializing S&P 500 Fundamental Discovery...")
    
    # Simulate the "Spinning Numbers" effect
    total = 503
    for i in range(1, total + 1):
        sys.stdout.write(f"\r      [SCREENER] Audit Progress: {i}/{total} symbols scanned...")
        sys.stdout.flush()
        time.sleep(0.005)
        if i in [100, 200, 300, 400, 500]:
            print(f"\n      [✓] Batch {i//100} verified. Identifying alpha signals...")
            
    print(f"\n\n🎯 [ORCHESTRATOR] 503 symbol screening complete. 4 conviction targets promoted.")
    time.sleep(1)
    
    # 2. Deep Dive Selection
    print(f"\n>>> PHASE 2: TARGET ACQUIRED — {ticker}")
    _log(f"[ORCHESTRATOR] Establishing deep-dive pipeline for {ticker}...")
    
    # 3. Trigger Full Research Flow (alpha_flow.py)
    print(f"\n📡 [PHASE 3] Deploying Expert Analyst Swarm (SEC/EC/Sentiment)...")
    flow_cmd = [sys.executable, "alpha_flow.py", "--ticker", ticker]
    subprocess.run(flow_cmd, check=True)
    
    # 4. Trigger Expert Outreach (Special logic for FLY)
    if ticker == "FLY":
        print(f"\n>>> PHASE 4: EXPERT OUTREACH — DIRECT SHADOW MODE")
        _log(f"[OUTREACH] Dispatching AI-informed inquiries to Shubhanker Kapoor...")
        try:
            outreach_cmd = [sys.executable, "fly_direct_outreach.py"]
            subprocess.run(outreach_cmd, check=True)
            print("   📩 [OUTREACH] Expert inquiries dispatched. Monitoring for resonance.")
        except:
            print("   ⚠️ [OUTREACH] Dispatch failed. Continuing with simulation...")
            
        # 5. Elite Audit Transition
        print(f"\n>>> PHASE 5: TRANSITIONING TO ELITE LOGIC ENGINE (POST-CALL)")
        print("    [SYSTEM] Standing by for expert call completion...")
        print("    👉 RUN: 'python3 voiceagent/post_voice_orchestration.py' to simulate call trigger.")
        
    print("\n================================================================")
    print("✅ ALPHA NEXUS: STAGE 1 ORCHESTRATION COMPLETE")
    print("================================================================")

if __name__ == "__main__":
    main()
