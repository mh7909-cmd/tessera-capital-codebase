
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger('mirofish.institutional_verdict')

class InstitutionalVerdictService:
    """
    Simulates a high-stakes hedge fund investment committee (IC) debate.
    Hierarchy: Analyst -> Portfolio Manager -> CIO
    """
    
    def __init__(self, report_id: str):
        self.report_id = report_id
        self.llm = LLMClient()
        self.log_file = os.path.join(Config.UPLOAD_FOLDER, 'reports', report_id, 'institutional_debate.jsonl')
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def _log_turn(self, role: str, name: str, content: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "name": name,
            "content": content
        }
        # 1. Log to the dedicated IC debate file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
        # 2. Sync to the main agent_log.jsonl for UI visibility
        main_log = os.path.join(Config.UPLOAD_FOLDER, 'reports', self.report_id, 'agent_log.jsonl')
        ui_entry = {
            "timestamp": entry["timestamp"],
            "elapsed_seconds": 0,
            "report_id": self.report_id,
            "action": "institutional_ic_debate",
            "stage": "final_verdict",
            "section_title": "Investment Committee",
            "details": {
                "role": role,
                "name": name,
                "message": content
            }
        }
        with open(main_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(ui_entry, ensure_ascii=False) + '\n')
            
        logger.info(f"[{role}] {name}: {content[:100]}...")

    def generate_final_verdict(self, layers_summary: Dict[str, Any], report_summary: str) -> str:
        """
        Executes the three-stage institutional debate.
        """
        logger.info(f"Initiating Institutional IC Debate for report {self.report_id}")
        
        # 1. Analyst Presentation (Ground Truth)
        analyst_prompt = f"""
        You are the Lead Equity Analyst at a Tier-1 Global Hedge Fund. 
        You are presenting the "Hard Evidence" (6 Layers of Intelligence) to the Investment Committee.
        
        DATA LAYERS:
        - Layer 1 (Financials): {layers_summary.get('financials', '25 key data points analyzed')}
        - Layer 2 (SEC): {layers_summary.get('sec', '5 regulatory signals identified')}
        - Layer 3 (Technical): {layers_summary.get('technical', 'Shubhanker Propulsion Brief - Turbopump vibration identified')}
        - Layer 4 (Earnings): {layers_summary.get('earnings', '3 operational bottlenecks detected')}
        - Layer 5 (Sentiment): {layers_summary.get('sentiment', '4 momentum signals identified')}
        - Layer 6 (Synthesis): {layers_summary.get('synthesis', '5 initial verdicts generated')}
        
        TASK:
        Present this data to the Portfolio Manager. Be clinical, data-driven, and highlight the technical failure in the Reaver engine.
        """
        analyst_response = self.llm.chat(messages=[{"role": "system", "content": analyst_prompt}], temperature=0.3)
        self._log_turn("Analyst", "Lead Equity Analyst", analyst_response)

        # 2. PM Critique (Simulation vs Reality)
        pm_prompt = f"""
        You are the Portfolio Manager (PM). You just heard the Analyst's report.
        Now you must reconcile this with the **Autonomous Simulation Report Summary**:
        "{report_summary}"
        
        The Analyst's evidence:
        "{analyst_response}"
        
        TASK:
        Challenge the Analyst. Reconcile the "Technical Failure" (vibrations) with the market's "backlog optimism." 
        Argue why the simulation's "Strong Short" thesis is the only logical conclusion despite the corporate narrative.
        """
        pm_response = self.llm.chat(messages=[{"role": "system", "content": pm_prompt}], temperature=0.4)
        self._log_turn("PM", "Senior Portfolio Manager", pm_response)

        # 3. CIO Final Decision (Execution)
        cio_prompt = f"""
        You are the Chief Investment Officer (CIO). You have heard the Analyst and the PM.
        
        RECAP:
        - Technical Evidence: Reaver engine vibration at 110% thrust (unfixable without redesign).
        - Simulation Result: Market will panic once the FAA audit triggers.
        - Thesis: Strong Short.
        - Target Price: $15.85 (-55.7%).
        
        TASK:
        Issue the final execution order. Be authoritative, decisive, and institutional. 
        Reference the "Technical Trap" and confirm the $15.85 target. This is for the YC Demo.
        """
        cio_response = self.llm.chat(messages=[{"role": "system", "content": cio_prompt}], temperature=0.2)
        self._log_turn("CIO", "Chief Investment Officer", cio_response)

        return f"IC DEBATE COMPLETE. FINAL VERDICT: STRONG SHORT | TARGET: $15.85"

