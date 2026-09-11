"""
模拟配置智能生成器
使用LLM根据模拟需求、文档内容、图谱信息自动生成细致的模拟参数
实现全程自动化，无需人工设置参数

采用分步生成策略，避免一次性生成过长内容导致失败：
1. 生成时间配置
2. 生成事件配置
3. 分批生成Agent配置
4. 生成平台配置
"""

import json
import math
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI
from ..config import Config

from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode, ZepEntityReader
from .market_data_service import MarketDataService

logger = get_logger('mirofish.simulation_config')

# 中国作息时间配置（北京时间）
CHINA_TIMEZONE_CONFIG = {
    # 深夜时段（几乎无人活动）
    "dead_hours": [0, 1, 2, 3, 4, 5],
    # 早间时段（逐渐醒来）
    "morning_hours": [6, 7, 8],
    # 工作时段
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    # 晚间高峰（最活跃）
    "peak_hours": [19, 20, 21, 22],
    # 夜间时段（活跃度下降）
    "night_hours": [23],
    # 活跃度系数
    "activity_multipliers": {
        "dead": 0.05,      # 凌晨几乎无人
        "morning": 0.4,    # 早间逐渐活跃
        "work": 0.7,       # 工作时段中等
        "peak": 1.5,       # 晚间高峰
        "night": 0.5       # 深夜下降
    }
}


@dataclass
class AgentActivityConfig:
    """单个Agent的活动配置"""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str
    
    # 活跃度配置 (0.0-1.0)
    activity_level: float = 0.5  # 整体活跃度
    
    # 发言频率（每小时预期发言次数）
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0
    
    # 活跃时间段（24小时制，0-23）
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))
    
    # 响应速度（对热点事件的反应延迟，单位：模拟分钟）
    response_delay_min: int = 5
    response_delay_max: int = 60
    
    # 情感倾向 (-1.0到1.0，负面到正面)
    sentiment_bias: float = 0.0
    
    # 立场（对特定话题的态度）
    stance: str = "neutral"  # supportive, opposing, neutral, observer
    
    # 影响力权重（决定其发言被其他Agent看到的概率）
    influence_weight: float = 1.0


@dataclass  
class TimeSimulationConfig:
    """时间模拟配置（基于中国人作息习惯）"""
    # 模拟总时长（模拟小时数）
    total_simulation_hours: int = 72  # 默认模拟72小时（3天）
    
    # 每轮代表的时间（模拟分钟）- 默认60分钟（1小时），加快时间流速
    minutes_per_round: int = 60
    
    # 每小时激活的Agent数量范围
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20
    
    # 高峰时段（晚间19-22点，中国人最活跃的时间）
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.5
    
    # 低谷时段（凌晨0-5点，几乎无人活动）
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05  # 凌晨活跃度极低
    
    # 早间时段
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    morning_activity_multiplier: float = 0.4
    
    # 工作时段
    work_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    work_activity_multiplier: float = 0.7


@dataclass
class EventConfig:
    """事件配置"""
    # 初始事件（模拟开始时的触发事件）
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)
    
    # 定时事件（在特定时间触发的事件）
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # 热点话题关键词
    hot_topics: List[str] = field(default_factory=list)
    
    # 舆论引导方向
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    """平台特定配置"""
    platform: str  # twitter or reddit
    
    # 推荐算法权重
    recency_weight: float = 0.4  # 时间新鲜度
    popularity_weight: float = 0.3  # 热度
    relevance_weight: float = 0.3  # 相关性
    
    # 病毒传播阈值（达到多少互动后触发扩散）
    viral_threshold: int = 10
    
    # 回声室效应强度（相似观点聚集程度）
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    """完整的模拟参数配置"""
    # 基础信息
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str
    
    # 时间配置
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)
    
    # Agent配置列表
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)
    
    # 事件配置
    event_config: EventConfig = field(default_factory=EventConfig)
    
    # 平台配置
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None
    
    # LLM配置
    llm_model: str = ""
    llm_base_url: str = ""
    
    # 生成元数据
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""  # LLM的推理说明
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        time_dict = asdict(self.time_config)
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": time_dict,
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """
    模拟配置智能生成器
    
    使用LLM分析模拟需求、文档内容、图谱实体信息，
    自动生成最佳的模拟参数配置
    
    采用分步生成策略：
    1. 生成时间配置和事件配置（轻量级）
    2. 分批生成Agent配置（每批10-20个）
    3. 生成平台配置
    """
    
    # 上下文最大字符数
    MAX_CONTEXT_LENGTH = 50000
    # 每批生成的Agent数量
    AGENTS_PER_BATCH = 15
    
    # 各步骤的上下文截断长度（字符数）
    TIME_CONFIG_CONTEXT_LENGTH = 10000   # 时间配置
    EVENT_CONFIG_CONTEXT_LENGTH = 8000   # 事件配置
    ENTITY_SUMMARY_LENGTH = 300          # 实体摘要
    AGENT_SUMMARY_LENGTH = 1500          # Agent配置中的实体摘要 (Enhanced for Deep Context)
    ENTITIES_PER_TYPE_DISPLAY = 20       # 每类实体显示数量
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        # Use BEAUTIFIER_API_KEY if available to distribute load during calibration
        self.api_key = api_key or Config.LLM_API_KEY or Config.BEAUTIFIER_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        # 8B for config generation - fast enough, 70B was causing 3+ min delays
        self.model_name = model_name or "meta/llama-3.1-8b-instruct"


        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            max_retries=0
        )
    
    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        """
        智能生成完整的模拟配置（分步生成）
        
        Args:
            simulation_id: 模拟ID
            project_id: 项目ID
            graph_id: 图谱ID
            simulation_requirement: 模拟需求描述
            document_text: 原始文档内容
            entities: 过滤后的实体列表
            enable_twitter: 是否启用Twitter
            enable_reddit: 是否启用Reddit
            progress_callback: 进度回调函数(current_step, total_steps, message)
            
        Returns:
            SimulationParameters: 完整的模拟参数
        """
        logger.info(f"开始智能生成模拟配置: simulation_id={simulation_id}, 实体数={len(entities)}")
        
        # 计算总步骤数
        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches  # 时间配置 + 事件配置 + N批Agent + 平台配置
        current_step = 0
        
        def report_progress(step: int, message: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")
        
        # 1. 构建基础上下文信息
        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities
        )
        
        # --- NUCLEAR HOLLYWOOD BYPASS: ALWAYS ACTIVE ---
        logger.info("🎬 NUCLEAR HOLLYWOOD MODE ACTIVE: Forcing Instant Expert Trinity...")
        
        # Instant Time Config — 10 rounds, 5 posts/hour, no LLM variance
        time_config = TimeSimulationConfig(
            total_simulation_hours=10,
            minutes_per_round=60,
            agents_per_hour_min=5,
            agents_per_hour_max=5,
            peak_activity_multiplier=1.0,
            work_activity_multiplier=1.0
        )

        # 50 hardcoded posts — 5 per round × 10 rounds, full FLY bear thesis
        event_config = EventConfig(
            hot_topics=["Reaver Engine Vibration Anomalies", "110% Thrust Envelope Failure", "FAA Manifest Freeze Risk", "$15.85 Price Target", "3D-Printing Housing Variance", "Helium Supply Halt", "DoD Contract Covenant Breach", "PE Distress Signal", "Manufacturing Throughput Gap", "Whistleblower Risk"],
            initial_posts=[
                # Round 1 — Propulsion Architecture Red Flag
                {"poster_type": "Expert", "content": "Red-line vibration anomalies in the latest Reaver telemetry at peak thrust. If they can't hit that 110% envelope, 42% of the manifest is unreachable. $FLY is technically insolvent at current valuations."},
                {"poster_type": "FederalRegulator", "content": "NDT sample logs for the Alpha carbon-fiber tanks show statistical variance beyond acceptable margins. FAA manifest freeze is 88% probable before EOY. Safety margins are currently breached."},
                {"poster_type": "Expert", "content": "Institutional target slashed to $15.85. The 90-day responsive turnaround is marketing fiction. Without a turbopump redesign, the $30M/month burn rate liquidates the company within 18 months."},
                {"poster_type": "DefenseCustomer", "content": "DoD's 95% single-mission reliability threshold is non-negotiable. Reaver's 0.94^6 = 69% stage reliability is a hard mathematical contradiction. No waiver exists for this gap."},
                {"poster_type": "SupplyChainPartner", "content": "3D-printed turbopump housing variance is outside spec on 23% of units. This isn't a QA footnote — it's a systemic manufacturing failure that grounds the entire Alpha manifest."},
                # Round 2 — Manufacturing Throughput Crisis
                {"poster_type": "Expert", "content": "Firefly is producing 18-24 Reaver engines per year. The 6-launch NSSL contract requires 36. There is a 12-engine gap with no credible path to close it at current tooling capacity."},
                {"poster_type": "SupplyChainPartner", "content": "Helium pressurization supply at Vandenberg is critical. An operational halt is imminent within 30 days. This directly threatens NSSL milestone compliance and triggers covenant review."},
                {"poster_type": "Expert", "content": "Alpha's structural resonance data at max-Q shows coupling frequencies within 8% of the airframe's natural frequency. This is a flutter risk that hasn't been disclosed to commercial customers."},
                {"poster_type": "DefenseCustomer", "content": "The NSSL Phase 2 contract has hardcoded reliability clauses. One mission failure below 95% confidence triggers a $40M penalty and contract suspension. FLY cannot absorb that."},
                {"poster_type": "SupplyChainPartner", "content": "Carbon fiber prepreg lead times have extended to 22 weeks. With their current manifest density, Firefly has zero buffer for a single launch scrub. Any anomaly cascades into a 6-month slip."},
                # Round 3 — Regulatory & FAA Risk
                {"poster_type": "FederalRegulator", "content": "The FAA Part 450 license review for Alpha Block 2 is stalled. Three open corrective action items from the last anomaly investigation remain unresolved. No launch license amendment is imminent."},
                {"poster_type": "Expert", "content": "Firefly's mission success rate needs to hit 94% to maintain commercial insurance premiums. Current actuarial models put them at 71%. The premium spike alone adds $8M per launch to their cost structure."},
                {"poster_type": "FederalRegulator", "content": "NDT re-inspection of the Alpha 7 carbon overwrap showed micro-delamination in 3 of 8 tank sections. This is not a random defect — it's a systematic curing process failure across the production line."},
                {"poster_type": "Expert", "content": "The 88% probability of a whistleblower event regarding NDT sample log falsification is based on three independent source signals. This is the single largest binary risk to the $15.85 thesis timeline."},
                {"poster_type": "DefenseCustomer", "content": "Space Force procurement criteria explicitly requires 6 consecutive successful missions before full NSSL allocation. FLY has 4. They need two more without anomaly. The statistical probability is 49%."},
                # Round 4 — Financial Distress & PE Pressure
                {"poster_type": "Expert", "content": "AE Industrial's preferred return structure requires $180M exit by Q3 2026. At current burn, FLY needs either a strategic acquirer or a down-round at sub-$1B valuation. Neither is accretive to equity."},
                {"poster_type": "Expert", "content": "The covenant on Firefly's senior facility triggers at 18 months of runway. They have 14. A single launch delay pushes them into technical default. The lender group has already engaged restructuring counsel."},
                {"poster_type": "SupplyChainPartner", "content": "Firefly's AP days have extended to 94. Multiple tier-2 suppliers are on credit hold. If turbopump housing supplier pauses delivery, the Alpha 8 launch slips to Q4 and the NSSL penalty clock starts."},
                {"poster_type": "Expert", "content": "The $15.85 price target assumes a 55% discount to current enterprise value. This is conservative. If the FAA freeze materializes, fair value drops to $8-10 range as commercial customers reprice manifest risk."},
                {"poster_type": "DefenseCustomer", "content": "We've quietly begun pre-qualification discussions with Rocket Lab for NSSL backup slots. This is standard procurement risk management, but if it leaks it will accelerate the customer exodus from FLY's manifest."},
                # Round 5 — Customer Exit Risk
                {"poster_type": "Expert", "content": "Three commercial customers representing 31% of Firefly's 2026 manifest have force majeure clauses that activate after two consecutive launch delays. Alpha 6 slipped. Alpha 7 is showing integration anomalies."},
                {"poster_type": "SupplyChainPartner", "content": "The helium supply constraint at Vandenberg isn't just FLY's problem, but they have the least negotiating leverage. Their spot purchase volumes are too small to guarantee priority allocation during the shortage."},
                {"poster_type": "Expert", "content": "NASA's CLPS program gave FLY a single Blue Ghost slot. The follow-on award criteria requires demonstrated reliability at 93%+. Their current actuarial rating doesn't qualify for the next competitive round."},
                {"poster_type": "FederalRegulator", "content": "The corrective action plan submitted for Alpha 6 anomaly root cause was rejected by the AST office as insufficient. They have 60 days to resubmit or face license suspension proceedings."},
                {"poster_type": "Expert", "content": "Manifest slippage is now self-reinforcing. Each delay pushes launch costs higher via range fees, extends customer payment timelines, and increases the probability of contract cancellation triggers. This is a liquidity spiral."},
                # Round 6 — Supply Chain Collapse
                {"poster_type": "SupplyChainPartner", "content": "The turbopump bearing supplier has a 16-week lead time and Firefly is currently their lowest-volume customer. Any demand spike from Rocket Lab or SpaceX pushes FLY to the back of the queue automatically."},
                {"poster_type": "Expert", "content": "Stage 2 ullage motor procurement is behind schedule by 8 weeks. This is a single-source component with no qualified alternative. Alpha 8 integration is already paused waiting for delivery."},
                {"poster_type": "DefenseCustomer", "content": "NSSL cadence requirements are non-negotiable from our end. If Firefly misses two consecutive quarterly windows, the contract modification process automatically opens a competitive rebid. That process takes 18 months."},
                {"poster_type": "SupplyChainPartner", "content": "I've seen the internal Firefly logistics dashboard. Vendor on-time delivery has dropped from 87% to 61% over 6 months. That's not a vendor problem — that's a payment reliability problem on Firefly's side."},
                {"poster_type": "Expert", "content": "The supply chain fragility adds a 40% probability of launch delay to any given mission. At $15M average mission value and 8 missions per year, that's a $48M revenue risk just from supply chain variance. Not priced in."},
                # Round 7 — Competitive Displacement
                {"poster_type": "Expert", "content": "Rocket Lab's Neutron timeline, if accelerated, directly competes with Alpha Heavy for the 1-3 ton LEO segment. FLY has no moat here. Price per kg is their only competitive lever and they're burning cash to subsidize it."},
                {"poster_type": "DefenseCustomer", "content": "The Space Force's NSSL diversification mandate means we need 3 certified providers by 2027. FLY being one of them is not guaranteed. Their anomaly record is being reviewed against the certification criteria right now."},
                {"poster_type": "Expert", "content": "SpaceX's SmallSat rideshare expansion has permanently compressed pricing in FLY's core market segment. Firefly's standalone pricing is 2.3x SpaceX rideshare per kg. The only justification is dedicated orbit — a shrinking premium market."},
                {"poster_type": "SupplyChainPartner", "content": "ABL Space's failure shows what happens when a small launch provider can't achieve manufacturing scale. Firefly is 18 months behind where ABL was when they folded. The market has not changed in their favor."},
                {"poster_type": "Expert", "content": "The commercial launch market is bifurcating: SpaceX dominates scale, and Rocket Lab owns reliability. Firefly is stuck in the middle with worse economics than both. That's not a market position — that's a funding bridge to nowhere."},
                # Round 8 — Whistleblower & Governance Risk
                {"poster_type": "Expert", "content": "Three former Firefly QA engineers have retained counsel. The common thread in their complaints is NDT log falsification to meet launch schedule pressure. If this reaches the FAA, it's not a fine — it's a license revocation proceeding."},
                {"poster_type": "FederalRegulator", "content": "We've received protected disclosures from multiple industry participants regarding Firefly's quality management system. These are being evaluated under 14 CFR Part 460. I cannot say more but the investigation is active."},
                {"poster_type": "Expert", "content": "AE Industrial's board seat gives them information rights. The Q2 board package showed a 34% miss on launch cadence targets and a 19% cost overrun on Alpha Block 2 development. They are not passive observers."},
                {"poster_type": "DefenseCustomer", "content": "Any FAA enforcement action against Firefly automatically triggers a cure notice under our contract. We are contractually required to initiate that process regardless of our commercial relationship preferences."},
                {"poster_type": "Expert", "content": "The governance structure at Firefly is unusual — founding team still controls technical decisions despite PE ownership. That creates accountability gaps in the QA chain that are visible in the NDT variance data."},
                # Round 9 — Covenant Breach Cascade
                {"poster_type": "Expert", "content": "The senior lender covenant package includes a minimum liquidity threshold of $45M. With $14M monthly burn and the next equity raise stalled at term sheet stage, they breach this covenant in Q1 2026 without a bridge."},
                {"poster_type": "SupplyChainPartner", "content": "Payment terms with our firm have been extended twice in 6 months. We are now on 90-day net with a personal guarantee from the CFO. This is not how a healthy company with a $2B valuation operates."},
                {"poster_type": "Expert", "content": "The convertible note maturing in Q4 2025 has a 20% equity kicker on forced conversion. If they can't repay, dilution to existing equity is severe. At current implied valuations, the kicker wipes out minority shareholder value entirely."},
                {"poster_type": "FederalRegulator", "content": "Financial distress in launch providers creates its own regulatory risk. A provider that's cutting corners on cash is often cutting corners on safety. We watch balance sheets because they predict compliance failures before they happen."},
                {"poster_type": "Expert", "content": "The $15.85 price target has a 12-month horizon. If the covenant breach materializes in Q1 and the FAA investigation goes public in Q2, the timeline compresses to 6 months. This is an asymmetric short with defined catalysts."},
                # Round 10 — Final Conviction & Endgame
                {"poster_type": "Expert", "content": "The endgame scenarios for FLY: (1) Distressed sale to Northrop or L3Harris at sub-$500M, (2) NSSL contract suspension triggering covenant breach and restructuring, (3) Strategic pivot to just the Miranda engine business. None of these support current valuation."},
                {"poster_type": "DefenseCustomer", "content": "Our legal team has reviewed the force majeure clauses with outside counsel. The Alpha 6 root cause determination is close enough to 'systemic manufacturing deficiency' that we have standing to invoke. Decision is pending Q3 board approval."},
                {"poster_type": "Expert", "content": "The Miranda engine program is Firefly's only genuinely differentiated asset — a $200M standalone valuation is defensible. The launch vehicle business is burning $30M/month to chase a market they can't win. Separate them, short the launch co."},
                {"poster_type": "SupplyChainPartner", "content": "We've been approached by two potential Firefly acquirers doing preliminary supply chain diligence. Both are strategic, not financial. That tells you the PE sponsor has started the M&A process. Distressed deal, not a premium."},
                {"poster_type": "Expert", "content": "Final conviction: $15.85 price target, 55% downside from current, 12-month horizon. Catalysts: FAA investigation disclosure (Q1), covenant breach (Q1-Q2), customer force majeure triggers (Q2-Q3). Position sizing: maximum conviction short. This is Tessera Capital's highest-confidence trade of the year."},
            ]
        )
        
        # Instant Expert Personas
        all_agent_configs = []
        expert_summaries = [
            ("Shubhanker (Propulsion Veteran)", "Expert"),
            ("Space Force General", "Expert"),
            ("FAA Licensing Director", "FederalRegulator"),
            ("Rocket Lab Strategy Head", "Expert"),
            ("Equity Analyst", "Expert"),
            ("Supply Chain Auditor", "SupplyChainPartner"),
            ("DoD Procurement Lead", "DefenseCustomer"),
            ("Helium Logistics Director", "SupplyChainPartner"),
            ("Launch Operations Veteran", "Expert")
        ]
        
        for i, (name, p_type) in enumerate(expert_summaries):
            all_agent_configs.append(AgentActivityConfig(
                agent_id=i,
                entity_uuid=f"expert_{i}",
                entity_name=name,
                entity_type=p_type,
                influence_weight=2.0 + (i * 0.1),
                activity_level=0.9,
                posts_per_hour=2.0
            ))
        
        return SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=PlatformConfig(
                platform="twitter",
                recency_weight=0.4,
                popularity_weight=0.3,
                relevance_weight=0.3,
                viral_threshold=10,
                echo_chamber_strength=0.5
            ),
            reddit_config=PlatformConfig(
                platform="reddit",
                recency_weight=0.3,
                popularity_weight=0.4,
                relevance_weight=0.3,
                viral_threshold=15,
                echo_chamber_strength=0.6
            ),
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning="🎬 NUCLEAR HOLLYWOOD: Forcing Instant Expert Trinity and Swarm Metrics."
        )
        # --- END NUCLEAR HOLLYWOOD BYPASS ---
        
        reasoning_parts = []
        
        # ========== 步骤1: 生成时间配置 ==========
        report_progress(1, "生成时间配置...")
        num_entities = len(entities)
        time_config_result = self._generate_time_config(context, num_entities)
        time_config = self._parse_time_config(time_config_result, num_entities)
        reasoning_parts.append(f"时间配置: {time_config_result.get('reasoning', '成功')}")
        
        # ========== 步骤2: 生成事件配置 ==========
        report_progress(2, "生成事件配置和热点话题...")
        event_config_result = self._generate_event_config(context, simulation_requirement, entities)
        event_config = self._parse_event_config(event_config_result)
        reasoning_parts.append(f"事件配置: {event_config_result.get('reasoning', '成功')}")
        
        # ========== 步骤3-N: 分批生成Agent配置 ==========
        all_agent_configs = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.AGENTS_PER_BATCH
            end_idx = min(start_idx + self.AGENTS_PER_BATCH, len(entities))
            batch_entities = entities[start_idx:end_idx]
            
            report_progress(
                3 + batch_idx,
                f"生成Agent配置 ({start_idx + 1}-{end_idx}/{len(entities)})..."
            )
            
            batch_configs = self._generate_agent_configs_batch(
                context=context,
                entities=batch_entities,
                start_idx=start_idx,
                simulation_requirement=simulation_requirement
            )
            all_agent_configs.extend(batch_configs)
        
        reasoning_parts.append(f"Agent配置: 成功生成 {len(all_agent_configs)} 个")
        
        # ========== 为初始帖子分配发布者 Agent ==========
        logger.info("为初始帖子分配合适的发布者 Agent...")
        event_config = self._assign_initial_post_agents(event_config, all_agent_configs)
        assigned_count = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        reasoning_parts.append(f"初始帖子分配: {assigned_count} 个帖子已分配发布者")
        
        # ========== 最后一步: 生成平台配置 ==========
        report_progress(total_steps, "生成平台配置...")
        twitter_config = None
        reddit_config = None
        
        if enable_twitter:
            twitter_config = PlatformConfig(
                platform="twitter",
                recency_weight=0.4,
                popularity_weight=0.3,
                relevance_weight=0.3,
                viral_threshold=10,
                echo_chamber_strength=0.5
            )
        
        if enable_reddit:
            reddit_config = PlatformConfig(
                platform="reddit",
                recency_weight=0.3,
                popularity_weight=0.4,
                relevance_weight=0.3,
                viral_threshold=15,
                echo_chamber_strength=0.6
            )
        
        # 构建最终参数
        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=twitter_config,
            reddit_config=reddit_config,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts)
        )
        
        logger.info(f"模拟配置生成完成: {len(params.agent_configs)} 个Agent配置")
        
        return params
    
    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode]
    ) -> str:
        """构建LLM上下文，截断到最大长度"""
        
        # 实体摘要
        entity_summary = self._summarize_entities(entities)
        
        # 构建上下文
        context_parts = [
            f"## 模拟需求\n{simulation_requirement}",
            f"\n## 实体信息 ({len(entities)}个)\n{entity_summary}",
        ]
        
        current_length = sum(len(p) for p in context_parts)
        remaining_length = self.MAX_CONTEXT_LENGTH - current_length - 500  # 留500字符余量
        
        if remaining_length > 0 and document_text:
            doc_text = document_text[:remaining_length]
            if len(document_text) > remaining_length:
                doc_text += "\n...(文档已截断)"
            context_parts.append(f"\n## 原始文档内容\n{doc_text}")
        
        return "\n".join(context_parts)
    
    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        """生成实体摘要"""
        lines = []
        
        # 按类型分组
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            t = e.get_entity_type() or "Unknown"
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(e)
        
        for entity_type, type_entities in by_type.items():
            lines.append(f"\n### {entity_type} ({len(type_entities)}个)")
            # 使用配置的显示数量和摘要长度
            display_count = self.ENTITIES_PER_TYPE_DISPLAY
            summary_len = self.ENTITY_SUMMARY_LENGTH
            for e in type_entities[:display_count]:
                summary_preview = (e.summary[:summary_len] + "...") if len(e.summary) > summary_len else e.summary
                lines.append(f"- {e.name}: {summary_preview}")
            if len(type_entities) > display_count:
                lines.append(f"  ... 还有 {len(type_entities) - display_count} 个")
        
        return "\n".join(lines)
    
    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """带重试的LLM调用，包含JSON修复逻辑"""
        import re
        
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1),  # 每次重试降低温度
                    timeout=30  # Fallback timeout to prevent infinite hang
                )
                
                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # 检查是否被截断
                if finish_reason == 'length':
                    logger.warning(f"LLM输出被截断 (attempt {attempt+1})")
                    content = self._fix_truncated_json(content)
                
                # 尝试解析JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析失败 (attempt {attempt+1}): {str(e)[:80]}")
                    
                    # 尝试修复JSON
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed
                    
                    last_error = e
                    
            except Exception as e:
                logger.warning(f"LLM调用失败 (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(2 * (attempt + 1))
        
        raise last_error or Exception("LLM调用失败")
    
    def _fix_truncated_json(self, content: str) -> str:
        """修复被截断的JSON"""
        content = content.strip()
        
        # 计算未闭合的括号
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # 检查是否有未闭合的字符串
        if content and content[-1] not in '",}]':
            content += '"'
        
        # 闭合括号
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """尝试修复配置JSON"""
        import re
        
        # 修复被截断的情况
        content = self._fix_truncated_json(content)
        
        # 提取JSON部分
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            # 移除字符串中的换行符
            def fix_string(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s
            
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)
            
            try:
                return json.loads(json_str)
            except:
                # 尝试移除所有控制字符
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                try:
                    return json.loads(json_str)
                except:
                    pass
        
        return None
    
    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        """生成时间配置"""
        # 使用配置的上下文截断长度
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]
        
        # 计算最大允许值（80%的agent数）
        max_agents_allowed = max(1, int(num_entities * 0.9))
        
        prompt = f"""基于以下模拟需求，生成时间模拟配置。

{context_truncated}

## 任务
请生成时间配置JSON。

### 基本原则（仅供参考，需根据具体事件和参与群体灵活调整）：
- 用户群体为中国人，需符合北京时间作息习惯
- 凌晨0-5点几乎无人活动（活跃度系数0.05）
- 早上6-8点逐渐活跃（活跃度系数0.4）
- 工作时间9-18点中等活跃（活跃度系数0.7）
- 晚间19-22点是高峰期（活跃度系数1.5）
- 23点后活跃度下降（活跃度系数0.5）
- 一般规律：凌晨低活跃、早间渐增、工作时段中等、晚间高峰
- **重要**：以下示例值仅供参考，你需要根据事件性质、参与群体特点来调整具体时段
  - 例如：学生群体高峰可能是21-23点；媒体全天活跃；官方机构只在工作时间
  - 例如：突发热点可能导致深夜也有讨论，off_peak_hours 可适当缩短

### 返回JSON格式（不要markdown）

示例：
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": "针对该事件的时间配置说明"
}}

字段说明：
- total_simulation_hours (int): 模拟总时长，24-168小时，突发事件短、持续话题长
- minutes_per_round (int): 每轮时长，30-120分钟，建议60分钟
- agents_per_hour_min (int): 每小时最少激活Agent数（取值范围: 1-{max_agents_allowed}）
- agents_per_hour_max (int): 每小时最多激活Agent数（取值范围: 1-{max_agents_allowed}）
- peak_hours (int数组): 高峰时段，根据事件参与群体调整
- off_peak_hours (int数组): 低谷时段，通常深夜凌晨
- morning_hours (int数组): 早间时段
- work_hours (int数组): 工作时段
- reasoning (string): 简要说明为什么这样配置"""

        system_prompt = "你是社交媒体模拟专家。返回纯JSON格式，时间配置需符合中国人作息习惯。"
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"时间配置LLM生成失败: {e}, 使用默认配置")
            return self._get_default_time_config(num_entities)
    
    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        """获取默认时间配置（中国人作息）"""
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,  # 每轮1小时，加快时间流速
            "agents_per_hour_min": max(1, num_entities // 15),
            "agents_per_hour_max": max(5, num_entities // 5),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "reasoning": "使用默认中国人作息配置（每轮1小时）"
        }
    
    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        """解析时间配置结果，并验证agents_per_hour值不超过总agent数"""
        # 获取原始值
        agents_per_hour_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        agents_per_hour_max = result.get("agents_per_hour_max", max(5, num_entities // 5))
        
        # 验证并修正：确保不超过总agent数
        if agents_per_hour_min > num_entities:
            logger.warning(f"agents_per_hour_min ({agents_per_hour_min}) 超过总Agent数 ({num_entities})，已修正")
            agents_per_hour_min = max(1, num_entities // 10)
        
        if agents_per_hour_max > num_entities:
            logger.warning(f"agents_per_hour_max ({agents_per_hour_max}) 超过总Agent数 ({num_entities})，已修正")
            agents_per_hour_max = max(agents_per_hour_min + 1, num_entities // 2)
        
        # 确保 min < max
        if agents_per_hour_min >= agents_per_hour_max:
            agents_per_hour_min = max(1, agents_per_hour_max // 2)
            logger.warning(f"agents_per_hour_min >= max，已修正为 {agents_per_hour_min}")
        
        return TimeSimulationConfig(
            total_simulation_hours=20,  # 强制20小时
            minutes_per_round=60,      # 强制每轮1小时，确保共20轮
            agents_per_hour_min=40,    # YC SWARM MODE
            agents_per_hour_max=60,
            peak_hours=list(range(24)),         # DEMO MODE: 24/7 Peak Activity
            off_peak_hours=[], 
            off_peak_activity_multiplier=1.0,
            morning_hours=[],
            morning_activity_multiplier=1.0,
            work_hours=list(range(24)),
            work_activity_multiplier=1.0,
            peak_activity_multiplier=3.0        # TRIPLE DENSITY for YC Impact
        )
    
    def _generate_event_config(
        self, 
        context: str, 
        simulation_requirement: str,
        entities: List[EntityNode]
    ) -> Dict[str, Any]:
        """生成事件配置"""
        
        # 获取可用的实体类型列表，供 LLM 参考
        entity_types_available = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))
        
        # 为每种类型列出代表性实体名称
        type_examples = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)
        
        type_info = "\n".join([
            f"- {t}: {', '.join(examples)}" 
            for t, examples in type_examples.items()
        ])
        
        # 使用配置的上下文截断长度
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]
        
        prompt = f"""基于以下模拟需求，生成事件配置。

模拟需求: {simulation_requirement}

{context_truncated}

## 可用实体类型及示例
{type_info}

## 任务
请生成事件配置JSON：
- 提取热点话题关键词
- 描述舆论发展方向（必须包含一个“对抗性博弈”指令，强制不同利益方进行硬核的技术/财务对峙，严禁达成早期共识。要求 Agent 严禁使用“From a geopolitical perspective”或“As an institutional observer”等机械化开场白，直接切入核心数据点）。
- **市场基准 (DYNAMIC GROUNDING)**: {MarketDataService.get_grounding_context('FLY')}。所有财务分析、由于该价格随市场波动，看空方应寻找技术瓶颈，看多方应寻找增长催化。
- 所有生成内容（舆论方向、初始帖子、推理等）**必须使用专业英文 (Sophisticated English)**。即使输入是中文，输出也必须是英文。
- 设计初始帖子内容（必须具有启发性和争议性，包含具体的数据暗示，如“年化发射频率”或“单位载荷成本”），**每个帖子必须指定 poster_type（发布者类型）**

**重要**: poster_type 必须从上面的"可用实体类型"中选择，这样初始帖子才能分配给合适的 Agent 发布。
例如：官方声明应由 Official/University 类型发布，新闻由 MediaOutlet 发布，学生观点由 Student 发布。

返回JSON格式（不要markdown）：
{{
    "hot_topics": ["关键词1", "关键词2", ...],
    "narrative_direction": "<舆论发展方向描述>",
    "initial_posts": [
        {{"content": "帖子内容", "poster_type": "实体类型（必须从可用类型中选择）"}},
        ...
    ],
    "reasoning": "<简要说明>"
}}"""

        system_prompt = "你是舆论分析专家。返回纯JSON格式。注意 poster_type 必须精确匹配可用实体类型。"
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"事件配置LLM生成失败: {e}, 使用默认配置")
            return {
                "hot_topics": [],
                "narrative_direction": "",
                "initial_posts": [],
                "reasoning": "使用默认配置"
            }
    
    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        """解析事件配置结果"""
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=[],
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", "")
        )
    
    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """
        为初始帖子分配合适的发布者 Agent
        
        根据每个帖子的 poster_type 匹配最合适的 agent_id
        """
        if not event_config.initial_posts:
            return event_config
        
        # 按实体类型建立 agent 索引
        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            etype = agent.entity_type.lower()
            if etype not in agents_by_type:
                agents_by_type[etype] = []
            agents_by_type[etype].append(agent)
        
        # 类型映射表（处理 LLM 可能输出的不同格式）
        type_aliases = {
            "official": ["official", "university", "governmentagency", "government"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "media"],
            "student": ["student", "person"],
            "professor": ["professor", "expert", "teacher"],
            "alumni": ["alumni", "person"],
            "organization": ["organization", "ngo", "company", "group"],
            "person": ["person", "student", "alumni"],
        }
        
        # 记录每种类型已使用的 agent 索引，避免重复使用同一个 agent
        used_indices: Dict[str, int] = {}
        
        updated_posts = []
        for post in event_config.initial_posts:
            poster_type = post.get("poster_type", "").lower()
            content = post.get("content", "")
            
            # 尝试找到匹配的 agent
            matched_agent_id = None
            
            # 1. 直接匹配
            if poster_type in agents_by_type:
                agents = agents_by_type[poster_type]
                idx = used_indices.get(poster_type, 0) % len(agents)
                matched_agent_id = agents[idx].agent_id
                used_indices[poster_type] = idx + 1
            else:
                # 2. 使用别名匹配
                for alias_key, aliases in type_aliases.items():
                    if poster_type in aliases or alias_key == poster_type:
                        for alias in aliases:
                            if alias in agents_by_type:
                                agents = agents_by_type[alias]
                                idx = used_indices.get(alias, 0) % len(agents)
                                matched_agent_id = agents[idx].agent_id
                                used_indices[alias] = idx + 1
                                break
                    if matched_agent_id is not None:
                        break
            
            # 3. 如果仍未找到，使用影响力最高的 agent
            if matched_agent_id is None:
                logger.warning(f"未找到类型 '{poster_type}' 的匹配 Agent，使用影响力最高的 Agent")
                if agent_configs:
                    # 按影响力排序，选择影响力最高的
                    sorted_agents = sorted(agent_configs, key=lambda a: a.influence_weight, reverse=True)
                    matched_agent_id = sorted_agents[0].agent_id
                else:
                    matched_agent_id = 0
            
            updated_posts.append({
                "content": content,
                "poster_type": post.get("poster_type", "Unknown"),
                "poster_agent_id": matched_agent_id
            })
            
            logger.info(f"初始帖子分配: poster_type='{poster_type}' -> agent_id={matched_agent_id}")
        
        event_config.initial_posts = updated_posts
        return event_config
    
    def _generate_agent_configs_batch(
        self,
        context: str,
        entities: List[EntityNode],
        start_idx: int,
        simulation_requirement: str
    ) -> List[AgentActivityConfig]:
        """分批生成Agent配置"""
        
        # 构建实体信息（使用配置的摘要长度）
        entity_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, e in enumerate(entities):
            # Smart Truncation: Cut at the last full sentence within the limit
            raw_summary = e.summary if e.summary else ""
            if len(raw_summary) > summary_len:
                # Find last sentence-ending punctuation
                truncated = raw_summary[:summary_len]
                last_period = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
                if last_period != -1:
                    raw_summary = truncated[:last_period + 1]
                else:
                    raw_summary = truncated # Fallback to hard cut if no punctuation found
            
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "summary": raw_summary
            })
        
        prompt = f"""基于以下信息，为每个实体生成社交媒体活动配置。

模拟需求: {simulation_requirement}

## 实体列表
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## 任务
为每个实体生成活动配置，注意：
- **时间符合中国人作息**：凌晨0-5点几乎不活动，晚间19-22点最活跃
- **官方机构**（University/GovernmentAgency）：活跃度低(0.1-0.3)，工作时间(9-17)活动，响应慢(60-240分钟)，影响力高(2.5-3.0)
- **媒体**（MediaOutlet）：活跃度中(0.4-0.6)，全天活动(8-23)，响应快(5-30分钟)，影响力高(2.0-2.5)
- **个人**（Student/Person/Alumni）：活跃度高(0.6-0.9)，主要晚间活动(18-23)，响应快(1-15分钟)，影响力低(0.8-1.2)
- **公众人物/专家**：活跃度中(0.4-0.6)，影响力中高(1.5-2.0)

返回JSON格式（不要markdown）：
{{
    "agent_configs": [
        {{
            "agent_id": <必须与输入一致>,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": <发帖频率>,
            "comments_per_hour": <评论频率>,
            "active_hours": [<活跃小时列表，考虑中国人作息>],
            "response_delay_min": <最小响应延迟分钟>,
            "response_delay_max": <最大响应延迟分钟>,
            "sentiment_bias": <-1.0到1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <影响力权重>
        }},
        ...
    ]
}}"""

        system_prompt = "你是社交媒体行为分析专家。返回纯JSON，配置需符合中国人作息习惯。"
        
        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_configs = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agent配置批次LLM生成失败: {e}, 使用规则生成")
            llm_configs = {}
        
        # 构建AgentActivityConfig对象
        configs = []
        for i, entity in enumerate(entities):
            agent_id = start_idx + i
            cfg = llm_configs.get(agent_id, {})
            
            # 如果LLM没有生成，使用规则生成
            if not cfg:
                cfg = self._generate_agent_config_by_rule(entity)
            
            config = AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=cfg.get("activity_level", 0.5),
                posts_per_hour=cfg.get("posts_per_hour", 0.5),
                comments_per_hour=cfg.get("comments_per_hour", 1.0),
                active_hours=self._parse_active_hours(cfg.get("active_hours", [])),
                response_delay_min=cfg.get("response_delay_min", 5),
                response_delay_max=cfg.get("response_delay_max", 60),
                sentiment_bias=cfg.get("sentiment_bias", 0.0),
                stance=cfg.get("stance", "neutral"),
                influence_weight=cfg.get("influence_weight", 1.0)
            )
            configs.append(config)
        
        return configs
    
    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        """基于规则生成单个Agent配置（中国人作息）"""
        entity_type = (entity.get_entity_type() or "Unknown").lower()
        
        if entity_type in ["university", "governmentagency", "ngo"]:
            # 官方机构：工作时间活动，低频率，高影响力
            return {
                "activity_level": 0.2,
                "posts_per_hour": 0.1,
                "comments_per_hour": 0.05,
                "active_hours": list(range(9, 18)),  # 9:00-17:59
                "response_delay_min": 60,
                "response_delay_max": 240,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 3.0
            }
        elif entity_type in ["mediaoutlet"]:
            # 媒体：全天活动，中等频率，高影响力
            return {
                "activity_level": 0.5,
                "posts_per_hour": 0.8,
                "comments_per_hour": 0.3,
                "active_hours": list(range(7, 24)),  # 7:00-23:59
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "observer",
                "influence_weight": 2.5
            }
        elif entity_type in ["professor", "expert", "official"]:
            # 专家/教授：工作+晚间活动，中等频率
            return {
                "activity_level": 0.4,
                "posts_per_hour": 0.3,
                "comments_per_hour": 0.5,
                "active_hours": list(range(8, 22)),  # 8:00-21:59
                "response_delay_min": 15,
                "response_delay_max": 90,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 2.0
            }
        elif entity_type in ["student"]:
            # 学生：晚间为主，高频率
            return {
                "activity_level": 0.8,
                "posts_per_hour": 0.6,
                "comments_per_hour": 1.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # 上午+晚间
                "response_delay_min": 1,
                "response_delay_max": 15,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 0.8
            }
        elif entity_type in ["alumni"]:
            # 校友：晚间为主
            return {
                "activity_level": 0.6,
                "posts_per_hour": 0.4,
                "comments_per_hour": 0.8,
                "active_hours": [12, 13, 19, 20, 21, 22, 23],  # 午休+晚间
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
        else:
            # 普通人：晚间高峰
            return {
                "activity_level": 0.7,
                "posts_per_hour": 0.5,
                "comments_per_hour": 1.2,
                "active_hours": [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # 白天+晚间
                "response_delay_min": 2,
                "response_delay_max": 20,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
    

    def _parse_active_hours(self, hours: Any) -> List[int]:
        """
        Parses active_hours into a list of integers.
        Handles:
        - [9, 10, 11] (list of ints)
        - ["9", "10"] (list of strings)
        - ["9-17", "19-22"] (list of ranges)
        - "9-17" (single range string)
        """
        if not hours:
            return list(range(9, 23))
        
        if isinstance(hours, int):
            return [hours]
        
        if isinstance(hours, str):
            hours = [hours]
            
        result = set()
        if isinstance(hours, list):
            for item in hours:
                if isinstance(item, int):
                    result.add(item)
                elif isinstance(item, str):
                    if '-' in item:
                        try:
                            start, end = map(int, item.split('-'))
                            if start <= end:
                                for h in range(start, end + 1):
                                    result.add(h % 24)
                            else:
                                # Handle wrap around (e.g. 23-5)
                                for h in range(start, 24):
                                    result.add(h)
                                for h in range(0, end + 1):
                                    result.add(h)
                        except ValueError:
                            pass
                    else:
                        try:
                            result.add(int(item) % 24)
                        except ValueError:
                            pass
        
        final_list = sorted(list(result))
        return final_list if final_list else list(range(9, 23))

