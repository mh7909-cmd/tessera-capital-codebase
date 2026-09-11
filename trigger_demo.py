#!/usr/bin/env python3
import sys
import subprocess
import os
import time

# --- MOCK VAPI DATA ---
TICKER = "FLY"
EXPERT = "Technical Architect"

def main():
    print("\n" + "="*60)
    print("   📡 FIREFLY AEROSPACE — MANUAL DEMO TRIGGER")
    print("   ⚠️  BYPASSING VOICE WEBHOOK FOR INSTANT ORCHESTRATION")
    print("="*60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    orchestrator_path = os.path.join(base_dir, "voiceagent", "post_voice_orchestration.py")
    
    if not os.path.exists(orchestrator_path):
        print(f"❌ Error: Orchestrator not found at {orchestrator_path}")
        return

    print(f"\n[SYSTEM] Simulating end-of-call report for {TICKER} [{EXPERT}]...")
    print(f"[SYSTEM] Launching full autonomous pipeline: Research -> Sim -> Trade\n")
    
    # Run the orchestrator in a background process
    try:
        # We use Popen so this trigger script can finish and show the user what's happening
        # but the actual work happens in the background.
        subprocess.Popen([sys.executable, orchestrator_path, TICKER, EXPERT], cwd=base_dir)
        
        print(f"✅ Handoff Successful.")
        print(f"🔗 Pipeline active. Monitoring UI for Phase 0 (Gmail Transcript)...")
        print(f"\nNext steps to watch:")
        print(f"1. Browser opens Gmail Inbox (80s discovery pause).")
        print(f"2. Simulation starts on localhost:5173.")
        print(f"3. Final Agent Debate & Alpaca execution in Diligence Hub.")
        print("\n" + "="*60 + "\n")
        
    except Exception as e:
        print(f"❌ Failed to launch orchestrator: {e}")

if __name__ == "__main__":
    main()
