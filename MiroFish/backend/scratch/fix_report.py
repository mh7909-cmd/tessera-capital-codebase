
import sys
import os
import json
import asyncio

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.report_agent import ReportAgent, ReportStatus
from app.config import Config

async def run_fix():
    print("🚀 Manual Report Generation Triggered for sim_01134566956e")
    
    # Target simulation
    sim_id = "sim_01134566956e"
    graph_id = "mirofish_90159956257e4c3d"
    requirement = "MISSION: HIGH-FIDELITY TECHNICAL & FINANCIAL AUDIT — FIREFLY AEROSPACE (FLY). Expose the structural contradiction between the reported $1.4B contract backlog and the mathematical stage-level reliability figures. OBJECTIVE: 1. Determine the 12-month adjusted price target for FLY based on the disclosed burn rates vs. milestone payments. 2. Specifically reconcile the 69% stage reliability figure against DoD mission-success requirements. 3. Identify the \"Cadence-Reliability Trap\": Can Firefly scale manufacturing without triggering a critical FAA stand-down? AGENT MANDATE — ADVERSARIAL STRESS TEST: (1) The live financial data shows specific EBITDA margins and cash flow figures — use THESE numbers, not estimates. (2) Reconcile the Piotroski F-Score and Altman Z-Score from the SEC signals with the bullish social sentiment — are retail investors ignoring institutional distress signals? (3) Model the scenario where Firefly achieves 4 launches in 2026 (not 6): what is the impact on burn rate, Series C timing, and NSSL milestone payments? (4) The 0.94^6 = 69% stage reliability vs DoD's 95% requirement is a hard mathematical contradiction with the $1.4B backlog. Resolve it."

    agent = ReportAgent(
        graph_id=graph_id,
        simulation_id=sim_id,
        simulation_requirement=requirement
    )
    
    print(f"--- Starting Report Generation ---")
    report = agent.generate_report()
    
    if report:
        print(f"✅ Success! Report ID: {report.report_id}")
        output_path = os.path.join(Config.UPLOAD_FOLDER, 'reports', report.report_id, 'report.md')
        if os.path.exists(output_path):
            with open(output_path, 'r') as f:
                content = f.read()
                print("\n--- SAMPLE REPORT PREVIEW ---\n")
                print(content[:2000] + "...")
        else:
            print("❌ Report file not found on disk.")
    else:
        print("❌ Report generation failed.")

if __name__ == "__main__":
    import asyncio
    # generate_report is synchronous in the class definition (it uses ThreadPoolExecutor internally)
    # but the way it's called in run_elite_audit might be different.
    # Looking at the class, it's a sync method.
    
    # Set Beautifier API Key if possible
    # (I'll just let the class find it in Config if it's there)
    
    import os
    os.environ['PYTHONPATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    from app.services.report_agent import ReportAgent
    
    # Note: the class definition I saw had generate_report as an instance method.
    
    # Running it
    sim_id = "sim_01134566956e"
    graph_id = "mirofish_90159956257e4c3d"
    requirement = "MISSION: HIGH-FIDELITY TECHNICAL & FINANCIAL AUDIT — FIREFLY AEROSPACE (FLY). Expose the structural contradiction between the reported $1.4B contract backlog and the mathematical stage-level reliability figures. OBJECTIVE: 1. Determine the 12-month adjusted price target for FLY based on the disclosed burn rates vs. milestone payments. 2. Specifically reconcile the 69% stage reliability figure against DoD mission-success requirements. 3. Identify the \"Cadence-Reliability Trap\": Can Firefly scale manufacturing without triggering a critical FAA stand-down? AGENT MANDATE — ADVERSARIAL STRESS TEST: (1) The live financial data shows specific EBITDA margins and cash flow figures — use THESE numbers, not estimates. (2) Reconcile the Piotroski F-Score and Altman Z-Score from the SEC signals with the bullish social sentiment — are retail investors ignoring institutional distress signals? (3) Model the scenario where Firefly achieves 4 launches in 2026 (not 6): what is the impact on burn rate, Series C timing, and NSSL milestone payments? (4) The 0.94^6 = 69% stage reliability vs DoD's 95% requirement is a hard mathematical contradiction with the $1.4B backlog. Resolve it."

    agent = ReportAgent(
        graph_id=graph_id,
        simulation_id=sim_id,
        simulation_requirement=requirement
    )
    
    print(f"--- Starting Report Generation ---")
    report = agent.generate_report()
    if report:
         print(f"✅ Success! Report ID: {report.report_id}")
    else:
         print("❌ Failed")
