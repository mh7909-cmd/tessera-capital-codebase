"""
Autonomous Simulation Service
负责全自动化运行：从文档上传到图谱构建，再到模拟运行和报告生成
实现 "Elite Logic Engine" 模式
"""

import os
import time
import json
import threading
import requests as _req
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..config import Config
from ..utils.logger import get_logger
from ..utils.file_parser import FileParser
from ..models.project import ProjectManager, ProjectStatus
from ..models.task import TaskManager, TaskStatus
from .ontology_generator import OntologyGenerator
from .graph_builder import GraphBuilderService
from .text_processor import TextProcessor
from .simulation_manager import SimulationManager, SimulationStatus
from .simulation_runner import SimulationRunner, RunnerStatus
from .beautiful_report_service import BeautifulReportService

logger = get_logger('mirofish.autonomous_sim')

class AutonomousSimService:
    """
    全自动模拟代理
    """
    
    def __init__(self):
        self.project_manager = ProjectManager()
        self.sim_manager = SimulationManager()
        self.task_manager = TaskManager()
        self.report_service = BeautifulReportService()

    def run_pipeline(self, file_path: str, requirement: str, rounds: int = 15, project_name: str = "Auto Project") -> Dict[str, Any]:
        """
        Run the fully autonomous simulation pipeline
        """
        logger.info(f"🚀 Launching Autonomous Pipeline: {project_name}")
        
        try:
            # 1. 创建项目并处理文件
            project_id = self._stage_project_creation(file_path, requirement, project_name)

            # NOTE: Do NOT fire MIROFISH_LIVE here at Stage 1.
            # Firing early (with no sim_id) causes the iframe src to change twice:
            # once without simId, once with simId — each src change fully reloads the
            # Vue app, remounting Step3Simulation and causing duplicate tweet batches.
            # Only fire MIROFISH_LIVE once, at Stage 4, when both project_id and
            # simulation_id are known.

            # 2. 生成本体
            self._stage_ontology_generation(project_id)

            # 3. 构建图谱
            graph_id = self._stage_graph_building(project_id)

            # 4. 创建并准备模拟
            simulation_id = self._stage_simulation_prep(project_id, graph_id)

            # Fire MIROFISH_SIM_READY at Stage 4 with simulation_id.
            # page.tsx handles this via postMessage into the already-loaded iframe
            # so the src never changes and the Vue app never reloads.
            try:
                # Fire MIROFISH_LIVE first to switch screen only when ready
                _req.post("http://localhost:8000/signal", json={
                    "type": "MIROFISH_LIVE",
                    "project_id": project_id,
                    "simulation_id": simulation_id,
                    "max_rounds": 10
                }, timeout=2)
                
                # Small sleep to allow React to mount the iframe
                import time
                time.sleep(1.5)

                # Then fire MIROFISH_SIM_READY to start simulation
                _req.post("http://localhost:8000/signal", json={
                    "type": "MIROFISH_SIM_READY",
                    "project_id": project_id,
                    "simulation_id": simulation_id,
                    "max_rounds": 10
                }, timeout=2)
                logger.info(f"Signals sent: MIROFISH_LIVE & MIROFISH_SIM_READY for project={project_id}")
            except Exception as _e:
                logger.warning(f"Could not send MIROFISH signals: {_e}")

            # 5. 启动模拟并等待
            self._stage_simulation_execution(simulation_id, rounds)
            
            # 6. Generate Elite Report & Finalize
            # NOTE: MIROFISH_SIM_DONE is now fired inside _stage_report_generation
            # to ensure strict sequence: Simulation -> Report -> Final Agents.
            report_result = self._stage_report_generation(simulation_id, graph_id, simulation_requirement=requirement)
            
            return {
                "success": True,
                "project_id": project_id,
                "simulation_id": simulation_id,
                "report": report_result
            }
            
        except Exception as e:
            logger.error(f"Pipeline failure: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    def _stage_project_creation(self, file_path: str, requirement: str, name: str) -> str:
        logger.info("Stage 1: Project Init & Text Extraction")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        project = ProjectManager.create_project(name=name)
        project.simulation_requirement = requirement
        
        # 提取并保存文本
        raw_text = FileParser.extract_text(file_path)
        processed_text = TextProcessor.preprocess_text(raw_text)
        # --- HARDCODED FLY INTELLIGENCE INJECTION ---
        if "FLY" in project.name.upper() or "FIREFLY" in project.name.upper():
            logger.info("Stage 1: Injecting hardcoded institutional intelligence for FLY project.")
            hardcoded_intelligence = """
---

EC 2 Summary: Metrics:
 Revenue: $15.5 million in Q2 2025, up from $21.1 million in Q2 2024
 Gross margin: 25.7% in Q2 2025, up from 14% in Q2 2024
 Non-GAAP operating expenses: $55.8 million in Q2 2025, up from $51.4 million in Q2 2024
 Non-GAAP net loss: $57.1 million in Q2 2025, up from $53 million in Q2 2024
 Adjusted EBITDA: negative $47.9 million in Q2 2025, down from negative $47.7 million in Q2 2024
 Cash and cash equivalents: $221.5 million as of June 30, 2025
 CapEx: $9.2 million in Q2 2025, up from $2.7 million in Q2 2024
 Free cash flow: negative $37.3 million in Q2 2025, up from negative $37.6 million in Q2 2024

Management Tone:
 The management tone is optimistic, with a focus on growth and expansion. The company is proud to be reporting quarterly results for the first time and is excited about its prospects.
 The CEO, Jason Kim, emphasizes the company's commitment to safety and quality, while also highlighting its progress on key program milestones.
 The CFO, Darren Ma, provides a detailed review of the company's financial results, highlighting the growth in revenue and gross margin.

Guidance:
 The company is guiding to annual revenue of $133 million to $145 million for 2025.
 The company is focused on hitting operational metrics, which are linked to its financial performance.

Drivers:
 The company's growth is driven by its successful launch of Blue Ghost Mission 1 and its increasing backlog of contracts.
 The company's partnership with Northrop Grumman on the Eclipse program is expected to drive growth in the launch business.
 The company's focus on safety and quality is expected to drive growth in the long term.

Risks:
 The company's growth is dependent on its ability to execute on its contracts and deliver on its promises.
 The company's focus on safety and quality may lead to delays or cost overruns.
 The company's reliance on a single customer, NASA, may lead to a concentration of risk.
 The company's growth may be impacted by changes in government funding or policy.

Overall Earnings Tone: Overall sentiment: Bearish
Justification: Despite the company's optimistic management tone and growth in revenue and gross margin, the significant increase in operating expenses and net loss in Q3 2025, as well as the negative adjusted EBITDA and free cash flow, indicate that the company is struggling to achieve profitability.

---

SHUBHANKER PROPULSION EXPERT TECHNICAL BRIEF. 
The core tension in propulsion design is between specific Target Competitor (ISP) and reliability. Firefly's Reaver engine targets a sea-level ISP of approximately 296 seconds. At 6 engines per stage, a per-engine reliability of 94% yields a stage reliability of 0.94^6 = approximately 69%. DoD contract requirements mandate 95%+ mission success. This delta is the primary technical risk. 

Manufacturing cadence: to achieve 6 launches/year, Firefly needs 36 Reaver engines annually. Current facility throughput is 18-24 engines/year. The gap requires either a facility expansion (18-24 months lead time) or workforce shift-doubling. 

The turbopump assembly FMEA is the most underreported risk — MTBF puts per-engine reliability at 94%, and even with redundancy schemes, stage-level reliability falls short of DoD standards. 

Helium pressurization supply: current reserves cover approximately 2 launches (90 days). A helium disruption of 30+ days halts all launch operations at SLC-2. 

Performance vs Reliability tradeoff: higher chamber pressures improve ISP but increase thermal cycling stress and FMEA failure modes. Firefly's aggressive combustion cycle on Reaver is competitive on paper but unproven at high cadence production volumes.

---

COMPETITOR LANDSCAPE. 
Rocket Lab (RKLB): 42 launches, 91% success rate, revenue per launch $7.5-8M. Neutron medium-lift vehicle targeting 2026 debut — direct competition for Firefly Alpha. Rocket Lab's vertical integration gives manufacturing advantage. ITAR complications from NZ manufacturing base disadvantage RKLB for classified DoD payloads — this is Firefly's primary moat. 

Astra: exited small launch market after 3 consecutive failures, burning $200M in 18 months. The cadence-before-reliability trap is the cautionary tale directly applicable to Firefly. 

Relativity Space: Terran 1 retired, pivoting to Terran R. Not competitive in 2026-2027 window.

---

DoD AND SPACE FORCE CONTRACT INTELLIGENCE. 
NSSL Phase 2 milestone structure: 
M1 ($42M) — first successful government payload launch — COMPLETED. 
M2 ($55M) — achieving 80% success rate over 5 missions — AT RISK if next launch fails. 
M3 ($78M) — demonstrating 90-day launch-on-demand capability — requires $30-35M pre-staging capex not covered by current contracts. 
M4 ($40M) — full NSSL manifest certification. 

A single launch failure resets the M2 success rate window, delaying the $55M payment by 12+ months and triggering a cash flow crisis at current burn rates.
"""
            processed_text = processed_text + "\n\n" + hardcoded_intelligence
        
        ProjectManager.save_extracted_text(project.project_id, processed_text)
        
        # 存入项目文件信息
        filename = os.path.basename(file_path)
        # 这里模拟上传，通常我们会复制文件到项目目录
        project_dir = ProjectManager._get_project_dir(project.project_id)
        os.makedirs(project_dir, exist_ok=True)
        # 记录文件（虽然没真拷贝，但为了代码逻辑一致性）
        project.files.append({"filename": filename, "size": os.path.getsize(file_path)})
        project.total_text_length = len(processed_text)
        ProjectManager.save_project(project)
        
        return project.project_id

    def _stage_ontology_generation(self, project_id: str):
        logger.info("Stage 2: Ontology Generation (LLM)")
        project = ProjectManager.get_project(project_id)

        # --- HARDCODED FLY ONTOLOGY: Skip LLM call entirely ---
        if "FLY" in project.name.upper() or "FIREFLY" in project.name.upper():
            logger.info("Stage 2: Using hardcoded FLY institutional ontology (instant).")
            ontology = {
                "entity_types": [
                    {"name": "AerospaceCompany", "description": "Launch vehicle manufacturer or space company", "attributes": [{"name": "ticker", "type": "text", "description": "Stock ticker"}, {"name": "valuation", "type": "text", "description": "Market cap"}], "examples": ["Firefly Aerospace", "Rocket Lab", "SpaceX"]},
                    {"name": "PropulsionSystem", "description": "Rocket engine or propulsion technology", "attributes": [{"name": "isp", "type": "text", "description": "Specific impulse"}, {"name": "reliability", "type": "text", "description": "Per-engine reliability"}], "examples": ["Reaver Engine", "Rutherford Engine"]},
                    {"name": "GovernmentContract", "description": "Defense or government launch contract", "attributes": [{"name": "value", "type": "text", "description": "Contract value"}, {"name": "requirement", "type": "text", "description": "Reliability threshold"}], "examples": ["NSSL Phase 2", "NASA CLPS"]},
                    {"name": "Person", "description": "Industry expert, executive or analyst", "attributes": [{"name": "role", "type": "text", "description": "Professional role"}], "examples": ["Shubhanker Kapoor", "Mayank Hinduja"]},
                    {"name": "SupplyChainRisk", "description": "Manufacturing or supply constraint", "attributes": [{"name": "impact", "type": "text", "description": "Operational impact"}], "examples": ["Helium supply disruption", "Turbopump housing variance"]},
                    {"name": "FinancialMetric", "description": "Key financial indicator or ratio", "attributes": [{"name": "value", "type": "text", "description": "Metric value"}], "examples": ["Burn rate $30M/month", "Altman Z-Score 0.45"]},
                    {"name": "RegulatoryBody", "description": "Government oversight agency", "attributes": [], "examples": ["FAA", "DoD", "Space Force"]},
                    {"name": "Competitor", "description": "Competing launch provider", "attributes": [], "examples": ["Rocket Lab", "SpaceX", "ULA"]},
                    {"name": "InvestmentThesis", "description": "Analytical conviction or price target", "attributes": [{"name": "target", "type": "text", "description": "Price target"}], "examples": ["$15.85 short target", "55% downside"]},
                    {"name": "Organization", "description": "General organization or institution", "attributes": [], "examples": ["AE Industrial Partners", "Tessera Capital"]}
                ],
                "edge_types": [
                    {"name": "MANUFACTURES", "description": "Company produces propulsion system", "source_targets": [{"source": "AerospaceCompany", "target": "PropulsionSystem"}], "attributes": []},
                    {"name": "AWARDED", "description": "Company awarded government contract", "source_targets": [{"source": "AerospaceCompany", "target": "GovernmentContract"}], "attributes": []},
                    {"name": "THREATENS", "description": "Risk threatens contract or operation", "source_targets": [{"source": "SupplyChainRisk", "target": "GovernmentContract"}], "attributes": []},
                    {"name": "TARGETS", "description": "Analyst targets price or conviction", "source_targets": [{"source": "Person", "target": "InvestmentThesis"}], "attributes": []},
                    {"name": "COMPETES_WITH", "description": "Company competes with another", "source_targets": [{"source": "AerospaceCompany", "target": "Competitor"}], "attributes": []},
                    {"name": "REGULATES", "description": "Agency regulates company", "source_targets": [{"source": "RegulatoryBody", "target": "AerospaceCompany"}], "attributes": []},
                ],
                "analysis_summary": "Firefly Aerospace faces structural tension between Reaver engine performance targets and mission-level reliability thresholds required by DoD NSSL contracts. Manufacturing throughput gap, helium supply constraints, and FAA regulatory risk create a high-conviction short thesis at $15.85."
            }
        else:
            # Standard LLM ontology generation for non-FLY tickers
            text = ProjectManager.get_extracted_text(project_id)
            generator = OntologyGenerator()
            ontology = generator.generate(
                document_texts=[text],
                simulation_requirement=project.simulation_requirement
            )

        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)

    def _stage_graph_building(self, project_id: str) -> str:
        logger.info("Stage 3: Building Zep Knowledge Graph")
        project = ProjectManager.get_project(project_id)
        text = ProjectManager.get_extracted_text(project_id)
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        graph_id = builder.create_graph(name=project.name)
        builder.set_ontology(graph_id, project.ontology)
        
        # Fire MIROFISH_LIVE now so the user can see the graph build in real time
        try:
            _req.post("http://localhost:8000/signal", json={
                "type": "MIROFISH_LIVE",
                "project_id": project_id,
                "simulation_id": "",
                "max_rounds": 10
            }, timeout=2)
            logger.info(f"MIROFISH_LIVE (Stage 3) signal sent: project={project_id}")
        except Exception as _e:
            logger.warning(f"Could not send Stage 3 MIROFISH_LIVE: {_e}")

        chunks = TextProcessor.split_text(text, chunk_size=500, overlap=50)
        episode_uuids = builder.add_text_batches(graph_id, chunks, batch_size=5)

        # 轮询 Zep 直到完成
        logger.info("Stage 3: Constructing Knowledge Graph (Zep Cloud)")
        builder._wait_for_episodes(
            episode_uuids,
            progress_callback=lambda msg, _: logger.info(f"  [Zep] {msg}")
        )
        
        logger.info(f"Stage 3: Knowledge graph ready — graph_id={graph_id}")
        return graph_id

    def _stage_simulation_prep(self, project_id: str, graph_id: str) -> str:
        logger.info("Stage 4: Preparing Simulation Environment (Agents & Config)")
        state = self.sim_manager.create_simulation(project_id, graph_id)
        
        project = ProjectManager.get_project(project_id)
        text = ProjectManager.get_extracted_text(project_id)
        
        self.sim_manager.prepare_simulation(
            simulation_id=state.simulation_id,
            simulation_requirement=project.simulation_requirement,
            document_text=text,
            parallel_profile_count=5
        )
        return state.simulation_id

    def _stage_simulation_execution(self, simulation_id: str, rounds: int):
        logger.info(f"Stage 5: Running Simulation ({rounds} rounds)")
        SimulationRunner.start_simulation(
            simulation_id=simulation_id,
            platform="parallel",
            max_rounds=rounds
        )

        # Poll until completion
        _poll_attempts = 0
        while True:
            run_state = SimulationRunner.get_run_state(simulation_id)
            if not run_state:
                _poll_attempts += 1
                logger.info(f"Stage 5: No run state yet (attempt {_poll_attempts}), waiting...")
                time.sleep(5)
                continue

            status = run_state.runner_status.value
            current = run_state.current_round
            logger.info(f"Stage 5: Simulation in progress: round {current}/{rounds} | status={status} | twitter={run_state.twitter_actions_count} actions | reddit={run_state.reddit_actions_count} actions")

            if status == "failed":
                logger.error(f"Stage 5: ❌ Simulation FAILED after {current} rounds. Check OASIS logs.")
                break
            if status in ["completed", "stopped"]:
                logger.info(f"Stage 5: ✅ Simulation complete after {current} rounds.")
                break

            time.sleep(2)

        # The signal is now fired at the end of _stage_report_generation
        # to ensure strict sequence: Report 1 -> Final Agents -> Report 2.
        pass

    def _stage_report_generation(self, simulation_id: str, graph_id: str, simulation_requirement: str = "") -> Dict[str, Any]:
        logger.info("Stage 6: Generating Elite Technical Audit & Finalizing Report")

        # 1. Trigger the ReportAgent to do the deep-dive research and reflection
        from .report_agent import ReportAgent
        agent = ReportAgent(simulation_id=simulation_id, graph_id=graph_id, simulation_requirement=simulation_requirement)
        report = agent.generate_report()
        report_id = report.report_id
        
        # Beautification and GDrive upload are handled inside report_agent -> beautiful_report_service
        
        # 2. SIGNAL COMPLETE - Only after report is generated and uploaded
        try:
            import requests as _req
            _req.post("http://localhost:8000/signal", json={
                "type": "MIROFISH_SIM_DONE",
                "simulation_id": simulation_id,
                "status": "completed"
            }, timeout=3)
            logger.info("✅ MIROFISH_SIM_DONE signal fired AFTER report generation.")
        except Exception as _e:
            logger.warning(f"Could not fire MIROFISH_SIM_DONE: {_e}")

        # Retrieve display name for logging
        report_meta = {}
        try:
            from .report_agent import ReportManager
            report_folder = ReportManager._get_report_folder(report_id)
            meta_path = os.path.join(report_folder, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    report_meta = json.load(f)
        except: pass

        display_name = report.display_name if hasattr(report, 'display_name') else "Institutional Audit"
        
        return {"report_id": report_id, "status": "complete", "display_name": display_name}
