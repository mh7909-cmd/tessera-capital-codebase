
import os
import sys
import argparse
import time

# 将项目根目录添加到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 设置环境变量，模拟 .env
from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))

from backend.app.services.autonomous_sim_service import AutonomousSimService

def main():
    parser = argparse.ArgumentParser(description='MiroFish Autonomous Simulation Agent')
    parser.add_argument('--file', type=str, required=True, help='Path to the knowledge document (DOCX/PDF/TXT)')
    parser.add_argument('--requirement', type=str, required=True, help='Simulation full prompt/requirement')
    parser.add_argument('--rounds', type=int, default=15, help='Number of simulation rounds (default: 15)')
    parser.add_argument('--name', type=str, default="Autonomous Simulation", help='Project Name')
    
    args = parser.parse_args()
    
    print("========================================")
    print("   MIROFISH AUTONOMOUS SIM AGENT        ")
    print("========================================")
    print(f"File: {args.file}")
    print(f"Rounds: {args.rounds}")
    print(f"Project: {args.name}")
    print("----------------------------------------")
    
    agent = AutonomousSimService()
    
    try:
        start_time = time.time()
        result = agent.run_pipeline(
            file_path=args.file,
            requirement=args.requirement,
            rounds=args.rounds,
            project_name=args.name
        )
        
        duration = (time.time() - start_time) / 60
        
        if result.get("success"):
            print("\n✅ SIMULATION PIPELINE COMPLETED SUCCESSFULLY!")
            print(f"Project ID: {result['project_id']}")
            print(f"Simulation ID: {result['simulation_id']}")
            print(f"Total Duration: {duration:.2f} minutes")
            print(f"\nFinal Report: {result['report'].get('display_name')}")
            print(f"Google Drive ID: {result['report'].get('gdrive_id')}")
            print("\nPlease check your Google Drive folder for the Verdict.")
        else:
            print(f"\n❌ PIPELINE FAILED: {result.get('error')}")
            
    except KeyboardInterrupt:
        print("\n⚠️ Simulation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
