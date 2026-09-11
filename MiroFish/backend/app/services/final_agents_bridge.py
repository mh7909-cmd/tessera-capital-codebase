
import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, Any
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.final_agents_bridge')

class FinalAgentsBridge:
    """
    Bridge to invoke the Advanced 'Final Agents' Hedge Fund simulation.
    Uses the system located in /Users/mayankhinduja/Desktop/Demo/Final Agents
    """
    
    def __init__(self, report_id: str):
        self.report_id = report_id
        self.final_agents_path = "/Users/mayankhinduja/Desktop/Demo/Final Agents"
        self.python_exe = sys.executable

    def run_simulation(self, ticker: str = "FLY", company_name: str = "Firefly Aerospace", mandate: str = None) -> Dict[str, Any]:
        """
        Runs the full LangGraph-based Final Agents debate and report generation.
        """
        logger.info(f"🚀 Launching FINAL AGENTS Hedge Fund Simulation for {ticker}...")
        
        # 1. Prepare Command
        # We run main.py from the Final Agents directory
        # NOTE: arg is --tickers (plural), --mandate does not exist as CLI arg
        cmd = [
            self.python_exe, "-u", "main.py",
            "--tickers", ticker,
            "--company-name", company_name,
            "--debate",
        ]

        # Inject dossier as context file so agents debate with real research data
        # miro_bridge writes this file before the simulation runs
        dossier_path = os.path.join("/Users/mayankhinduja/Desktop/Demo/MiroFish/tmp", f"{ticker}_dossier.txt")
        if not os.path.exists(dossier_path):
            dossier_path = os.path.join("/Users/mayankhinduja/Desktop/Demo/MiroFish/tmp", f"{ticker}_transcript.txt")
        if os.path.exists(dossier_path):
            cmd.extend(["--context-file", dossier_path])
            logger.info(f"Injecting institutional dossier into Final Agents: {dossier_path}")
        
        try:
            # 2. Execute Subprocess with streaming output
            process = subprocess.Popen(
                cmd,
                cwd=self.final_agents_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env={**os.environ, "PYTHONPATH": self.final_agents_path}
            )
            
            full_output = []
            for line in iter(process.stdout.readline, ''):
                # Print to stdout for the UI bridge to capture
                print(line, end='')
                sys.stdout.flush()
                full_output.append(line)
            
            process.stdout.close()
            return_code = process.wait()
            
            if return_code != 0:
                logger.error(f"Final Agents execution failed with code {return_code}")
                return {"success": False, "error": "Process failed"}
            
            logger.info("Final Agents simulation completed successfully.")
            
            # 3. Locate the generated debate log
            # DebateOrchestrator writes to debate_logs/{ticker}_{date}.json
            today_str = datetime.now().strftime("%Y-%m-%d")
            log_pattern = os.path.join(self.final_agents_path, "debate_logs", f"{ticker}_{today_str}.json")
            
            debate_content = {}
            if os.path.exists(log_pattern):
                with open(log_pattern, 'r') as f:
                    debate_content = json.load(f)
            
            # 4. Locate the generated thesis report
            # report_gen.py writes to reports/{ticker}_thesis_{timestamp}.docx
            report_pattern = os.path.join(self.final_agents_path, "reports", f"{ticker}_thesis_*.docx")
            import glob
            report_files = glob.glob(report_pattern)
            latest_report = max(report_files, key=os.path.getmtime) if report_files else None
            
            # 5. Sync logs to MiroFish UI
            self._sync_to_ui(debate_content)
            
            return {
                "success": True,
                "debate": debate_content,
                "report_path": latest_report,
                "console_output": "\n".join(full_output)
            }
            
        except Exception as e:
            logger.error(f"Error in FinalAgentsBridge: {str(e)}")
            return {"success": False, "error": str(e)}

    def _sync_to_ui(self, debate: Dict[str, Any]):
        """
        Parses the Final Agents debate transcript and syncs it to the MiroFish 'Talking' UI.
        """
        if not debate:
            return
            
        main_log = os.path.join(Config.UPLOAD_FOLDER, 'reports', self.report_id, 'agent_log.jsonl')
        transcript = debate.get("transcript", {})
        
        # Round 1: Analysts
        round1 = transcript.get("round1", {})
        for agent_id, signal in round1.items():
            self._write_ui_entry(main_log, "Institutional Analyst", agent_id.replace("_agent", "").title(), signal.get("reasoning", ""))
            
        # Devil's Advocate
        devil = transcript.get("devil_advocate", {})
        if devil:
            self._write_ui_entry(main_log, "Devil's Advocate", "Risk Auditor", devil.get("critique", ""))
            
        # Meta Synthesis (CIO / Adjudication)
        meta = debate.get("meta_summary", "")
        if meta:
            self._write_ui_entry(main_log, "Chief Investment Officer", "CIO / Meta Agent", meta)
            
        # Final Execution Decision (Portfolio Manager)
        # Portfolio Manager makes the final 'Action' and 'Quantity' call
        transcript_full = debate.get("transcript", {})
        # Note: In the real LangGraph, the PM's output is in the final state, 
        # but we can peek at the debate log's meta_summary which usually informs it.
        # However, to be precise, let's look for the 'signal' and 'position_size_pct'.
        signal = debate.get("signal", "hold").upper()
        size = debate.get("position_size_pct", 0)
        thesis = debate.get("meta_summary", "")
        
        pm_message = f"EXECUTION ORDER: {signal} position authorized. Target size: {size}% of portfolio. Reasoning: {thesis}"
        self._write_ui_entry(main_log, "Portfolio Manager", "PM / Lead Executioner", pm_message)

    def _write_ui_entry(self, log_path: str, role: str, name: str, message: str):
        if not message: return
        entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": 0,
            "report_id": self.report_id,
            "action": "institutional_ic_debate",
            "stage": "final_verdict",
            "section_title": "Final Institutional Argument",
            "details": {
                "role": role,
                "name": name,
                "message": str(message)[:2000] # Cap for UI
            }
        }
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

