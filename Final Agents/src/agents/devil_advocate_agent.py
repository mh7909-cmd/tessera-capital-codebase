"""Devil's advocate: attacks consensus; surfaces overlooked risks and false assumptions."""

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Literal

from src.graph.state import AgentState
from src.utils.llm import call_llm


class DevilAdvocateOutput(BaseModel):
    """Structured output for the devil's advocate (no directional trade thesis)."""

    agent: str = "devil_advocate"
    reasoning_steps: list[str] = Field(
        default_factory=list,
        description="Steps 1-5: philosophy (no position), attack plan, key miss, top risk, what would flip view",
    )
    overlooked_risks: list[str] = Field(default_factory=list)
    false_assumptions: list[str] = Field(default_factory=list)
    signal: Literal["neutral"] = "neutral"
    score: int = 0

    @field_validator("reasoning_steps", mode="before")
    @classmethod
    def pad_reasoning_steps(cls, v):
        """Pad reasoning_steps to at least 5 items if the 8B model only provides fewer."""
        if not isinstance(v, list):
            v = [str(v)]
        while len(v) < 5:
            v.append("Institutional risk factor identified.")
        return v[:8]  # cap at 8

    @field_validator("signal", mode="before")
    @classmethod
    def force_neutral_signal(cls, v):
        """Devil's advocate takes NO position — always neutral regardless of LLM output."""
        return "neutral"


# Double braces: ChatPromptTemplate treats single { } as variables; JSON must be escaped.
_DEVIL_PROMPT = """You take NO investment position. Your role is to stress-test consensus by identifying overlooked risks and false assumptions.

ADAPTIVE INTELLIGENCE RULES (Institutional Priority):
1. Prioritize 'research_context' (primary documents) over external API data.
2. If 'research_context' contradicts API metrics, favor the research findings to identify flaws in the API-driven consensus.
3. If API metrics are 'Insufficient data', use the documents to synthesize a critique.

Output ONLY valid JSON:
{{
  "agent": "devil_advocate",
  "reasoning_steps": ["step1", "step2", "step3", "step4", "step5"],
  "overlooked_risks": ["...", "..."],
  "false_assumptions": ["...", "..."],
  "signal": "neutral",
  "score": 0
}}
"""


def devil_advocate_analyze(
    state: AgentState,
    ticker: str,
    agent_outputs: dict[str, object],
    agent_id: str = "devil_advocate_agent",
) -> DevilAdvocateOutput:
    """
    Given other agents' per-ticker payloads, find gaps and challenge consensus.

    Parameters
    ----------
    agent_outputs
        Map of analyst agent_id -> payload for this ticker.
    """
    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the devil's advocate in an investment committee. " + _DEVIL_PROMPT,
            ),
            (
                "human",
                "Ticker: {ticker}\nOther agents' outputs (JSON):\n{blob}\nRespond with one JSON object only.",
            ),
        ]
    )
    blob = json.dumps(agent_outputs, default=str, separators=(",", ":"), ensure_ascii=False)
    prompt = template.invoke({"ticker": ticker, "blob": blob[:120000]})

    def _fallback() -> DevilAdvocateOutput:
        return DevilAdvocateOutput(
            reasoning_steps=[
                "I take no position; I stress-test the group thesis.",
                "The group may overweight near-term quality metrics.",
                "I assign score 0 by mandate.",
                "Tail risks and correlation shocks are the usual blind spots.",
                "I would change my critique if forensic accounting disproved fraud concerns.",
            ],
            overlooked_risks=["Liquidity gaps in stress", "Key-person risk"],
            false_assumptions=["Stable cost of capital", "Linear growth extrapolation"],
        )

    return call_llm(
        prompt=prompt,
        pydantic_model=DevilAdvocateOutput,
        agent_name=agent_id,
        state=state,
        default_factory=_fallback,
    )
