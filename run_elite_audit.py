import os
import sys
import subprocess
import requests
import time

def check_bridge():
    """Verify if the signal bridge is running on port 8000."""
    try:
        requests.get("http://127.0.0.1:8000/health", timeout=1)
        return True
    except:
        return False

def run_elite_audit():
    print("================================================================")
    print("🚀  MIROFISH ELITE LOGIC ENGINE: AUTONOMOUS AUDIT ENTRYPOINT  🚀")
    print("================================================================")
    
    BASE_DIR = "/Users/mayankhinduja/Desktop/Demo"
    TICKER = "FLY"
    
    # 0. Check for Signal Bridge
    if not check_bridge():
        print("⚠️  WARNING: api_bridge.py is not running on port 8000.")
        print("    Real-time dashboard signals will be disabled.")
        print("    Run it in a separate terminal: python3 api_bridge.py\n")

    # 1. Run Intelligence Bridge (Google Sheets + Hardcoded Transcript)
    print(f"\n📡 Phase 1: Securing live intelligence for {TICKER} from Google Sheets...")
    bridge_cmd = [sys.executable, "mirofish_bridge.py", TICKER]
    try:
        # Silence bridge output to prevent focus stealing
        subprocess.run(bridge_cmd, check=True, cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Intelligence Bridge Secured.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Intelligence Bridge Failed: {e}")
        sys.exit(1)

    # 2. Trigger Orchestrator (Simulation + Report + Final Debate)
    print(f"\n🌪️ Phase 2: Launching Post-Voice Orchestration (Simulation: 10 Rounds)...")
    orchestrator_path = os.path.join(BASE_DIR, "voiceagent", "post_voice_orchestration.py")
    orch_cmd = [sys.executable, orchestrator_path, TICKER]
    
    try:
        # 3. Focus Lock: Brief pause before launching the visual overlay
        print("\n🌪️  PREPARING DASHBOARD OVERLAY... (Screen will lock on MiroFish in 3s)")
        time.sleep(3)
        
        # We use a subprocess.run to block until the entire demo flow is complete
        # Note: orchestrator now handles its own internal silencing
        subprocess.run(orch_cmd, check=True, cwd=BASE_DIR)
        
        print("\n================================================================")
        print("✅ ELITE LOGIC ENGINE AUDIT COMPLETE: VERDICT SECURED")
        print("================================================================")
        
        # 4. PERSISTENCE: Block exit to keep focus on MiroFish
        print("\n📂 MISSION COMPLETE.")
        print("👉 Press [ENTER] in this terminal ONLY when you are ready to close the demo.")
        input() 
    except subprocess.CalledProcessError as e:
        print(f"❌ Orchestration Failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Demo ended by user.")
        sys.exit(0)

if __name__ == "__main__":
    run_elite_audit()
