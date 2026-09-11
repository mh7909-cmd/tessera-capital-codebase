"""Shared chain-of-thought (CoT) JSON schema and helpers for analyst agents.

Used by persona agents (LLM) and deterministic agents so downstream debate and
portfolio code can rely on a consistent shape: score (-100..100), reasoning_steps,
conviction_reason, invalidation_condition, plus legacy signal/confidence/reasoning.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import Literal


class CotAgentStructuredOutput(BaseModel):
    """Structured LLM output for chain-of-thought analyst responses."""

    agent: str
    reasoning_steps: list[str] = Field(
        min_length=5,
        max_length=8,
        description="Steps 1-5: philosophy, criteria analysis, score rationale, conviction, invalidation",
    )
    score: int = Field(ge=-100, le=100)
    conviction_reason: str
    invalidation_condition: str
    signal: Literal["bullish", "bearish", "neutral"]


# Braces doubled for LangChain ChatPromptTemplate (literal JSON example, not template vars).
COT_SYSTEM_SUFFIX = """
Chain-of-thought (required before you answer):
Step 1: State your investment philosophy in 1 sentence.
Step 2: Analyze the company across 3-5 key criteria specific to your persona.
Step 3: Assign a score from -100 (max bearish) to +100 (max bullish).
Step 4: State your single highest-conviction reason.
Step 5: State the one thing that would make you completely wrong.

Output ONLY valid JSON with this exact shape (no markdown fences):
{{
  "agent": "<your_agent_id>",
  "reasoning_steps": ["step1 text", "step2 text", "step3 text", "step4 text", "step5 text"],
  "score": <integer from -100 to 100>,
  "conviction_reason": "<short string>",
  "invalidation_condition": "<short string>",
  "signal": "bullish" | "bearish" | "neutral"
}}
The first element of reasoning_steps must be Step 1, the second Step 2, etc.
"""


def confidence_from_cot_score(score: int) -> int:
    """Map absolute score magnitude to 0-100 confidence for legacy consumers."""
    return min(100, max(0, abs(int(score))))


def signal_confidence_to_score(signal: str, confidence: float | int) -> int:
    """Map directional signal + confidence into -100..100."""
    c = float(confidence)
    c = max(0.0, min(100.0, c))
    mag = int(round(c))
    if signal == "bullish":
        return mag
    if signal == "bearish":
        return -mag
    # neutral: small magnitude near 0
    return int(round((mag / 100.0) * 25)) - 12


def cot_to_analyst_payload(
    cot: CotAgentStructuredOutput,
    *,
    reasoning_legacy: Any | None = None,
) -> dict[str, Any]:
    """Merge CoT output with legacy portfolio fields."""
    conf = confidence_from_cot_score(cot.score)
    out: dict[str, Any] = {
        "agent": cot.agent,
        "reasoning_steps": cot.reasoning_steps,
        "score": cot.score,
        "conviction_reason": cot.conviction_reason,
        "invalidation_condition": cot.invalidation_condition,
        "signal": cot.signal,
        "confidence": conf,
        "reasoning": cot.conviction_reason,
    }
    if reasoning_legacy is not None:
        out["reasoning"] = reasoning_legacy
    return out


def default_cot(agent_key: str) -> CotAgentStructuredOutput:
    """Safe fallback when the LLM fails to return valid structured output."""
    return CotAgentStructuredOutput(
        agent=agent_key,
        reasoning_steps=[
            "Insufficient data for a full thesis.",
            "Criteria could not be evaluated.",
            "Default score 0.",
            "No conviction.",
            "N/A",
        ],
        score=0,
        conviction_reason="Insufficient data",
        invalidation_condition="N/A",
        signal="neutral",
    )


def enrich_deterministic_cot(
    *,
    agent_key: str,
    philosophy: str,
    criteria_bullets: list[str],
    signal: str,
    confidence: float | int,
    conviction_reason: str,
    invalidation_condition: str,
    reasoning_legacy: Any | None = None,
) -> dict[str, Any]:
    """Build a CoT-shaped record for non-LLM agents (technicals, fundamentals, etc.)."""
    sc = signal_confidence_to_score(signal, confidence)
    bullets = criteria_bullets[:5]
    while len(bullets) < 3:
        bullets.append("(not enough criteria)")
    steps = [
        philosophy,
        "Criteria: " + "; ".join(bullets),
        f"Score {sc} derived from signal={signal} and confidence={confidence}.",
        conviction_reason,
        invalidation_condition,
    ]
    cot = CotAgentStructuredOutput(
        agent=agent_key,
        reasoning_steps=steps,
        score=sc,
        conviction_reason=conviction_reason,
        invalidation_condition=invalidation_condition,
        signal=signal if signal in ("bullish", "bearish", "neutral") else "neutral",
    )
    return cot_to_analyst_payload(cot, reasoning_legacy=reasoning_legacy)
