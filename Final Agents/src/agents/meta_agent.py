"""Meta / adjudicator agent: weighs other agents, regime-adjusted, produces final conviction."""

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing_extensions import Literal

from src.graph.state import AgentState
from src.utils.llm import call_llm


class MetaAgentOutput(BaseModel):
    """Final synthesis after debate."""

    agent: str = "meta_agent"
    conviction_score: float = Field(ge=-100, le=100, description="Final -100..100 conviction")
    position_size_pct: float = Field(ge=0, le=5, description="Recommended % of portfolio, cap 5%")
    investment_thesis: str = Field(description="Exactly three sentences")
    signal: Literal["bullish", "bearish", "neutral"]


def run_meta_synthesis(
    state: AgentState,
    ticker: str,
    debate_transcript: dict[str, object],
    spy_recent_return_pct: float | None,
    agent_id: str = "meta_agent",
) -> MetaAgentOutput:
    """
    Produce final conviction using full debate transcript and optional SPY regime.

    Uses rolling accuracy weights from FeedbackTracker when available.
    """
    regime = "neutral"
    if spy_recent_return_pct is not None:
        regime = "bull" if spy_recent_return_pct >= 0 else "bear"

    weights: dict[str, float] = {}
    try:
        from src.feedback_tracker import FeedbackTracker

        weights = FeedbackTracker().get_agent_weights()
    except Exception:
        weights = {}

    weights_blob = json.dumps(weights, separators=(",", ":"), ensure_ascii=False) if weights else "{}"

    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the chief investment officer synthesizing a multi-agent debate.\n"
                f"Market regime from recent SPY return: {regime} (numeric: {spy_recent_return_pct}).\n"
                "ADAPTIVE INTELLIGENCE RULES (Institutional Priority):\n"
                "1. Prioritize 'research_context' over external API data.\n"
                "2. If 'research_context' contradicts API metrics, favor the research.\n"
                "3. If API metrics are 'Insufficient data', use the documents to synthesize an opinion.\n"
                "Weighting policy: in bear regimes, lean more on value/defensive agents; "
                "in bull regimes, lean more on growth/macro momentum agents. "
                "Use agent_accuracy weights when provided as multipliers (agent_name -> float).\n"
                "Cap recommended position size at 5% of portfolio.\n"
                "investment_thesis must be exactly three sentences.\n"
                "Return JSON only:\n"
                "{{\n"
                '  "agent": "meta_agent",\n'
                '  "conviction_score": <float -100..100>,\n'
                '  "position_size_pct": <float 0..5>,\n'
                '  "investment_thesis": "<three sentences>",\n'
                '  "signal": "bullish" | "bearish" | "neutral"\n'
                "}}\n",
            ),
            (
                "human",
                "Ticker: {ticker}\n"
                "Agent accuracy weights (optional):\n{weights}\n"
                "Debate transcript:\n{transcript}\n"
                "Respond with one JSON object only.",
            ),
        ]
    )
    tr = json.dumps(debate_transcript, default=str, separators=(",", ":"), ensure_ascii=False)
    prompt = template.invoke(
        {
            "ticker": ticker,
            "weights": weights_blob,
            "transcript": tr[:200000],
        }
    )

    def _fallback() -> MetaAgentOutput:
        return MetaAgentOutput(
            conviction_score=0.0,
            position_size_pct=0.0,
            investment_thesis="Insufficient data to conclude. "
            "The debate transcript did not yield a confident edge. "
            "Default to no position until evidence improves.",
            signal="neutral",
        )

    return call_llm(
        prompt=prompt,
        pydantic_model=MetaAgentOutput,
        agent_name=agent_id,
        state=state,
        default_factory=_fallback,
    )
