"""Macro-oriented analyst: sector forces, rates, FX, geopolitics, commodities."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agents.cot_schema import (
    COT_SYSTEM_SUFFIX,
    CotAgentStructuredOutput,
    cot_to_analyst_payload,
    default_cot,
)
from src.graph.state import AgentState, show_agent_reasoning
from src.tools.api import get_financial_metrics, get_prices, prices_to_df
from src.utils.api_key import get_api_key_from_state
from src.utils.llm import call_llm
from src.utils.progress import progress


def global_macro_analyst_agent(state: AgentState, agent_id: str = "global_macro_analyst"):
    """Top-down macro view per ticker using fundamentals + optional SPY context."""
    data = state["data"]
    end_date = data["end_date"]
    start_date = data["start_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")
    out: dict[str, dict] = {}

    spy_ctx = _spy_recent_return(start_date, end_date, api_key)

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "Macro context")
        metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=3, api_key=api_key)
        facts = {
            "ticker": ticker,
            "metrics": [m.model_dump() for m in (metrics or [])],
            "research_context": state["data"].get("research_context", "No external documents provided."),
        }
        progress.update_status(agent_id, ticker, "Generating macro assessment")
        cot = _generate_macro_output(ticker, facts, state, agent_id)
        out[ticker] = cot_to_analyst_payload(cot)
        progress.update_status(agent_id, ticker, "Done", analysis=cot.conviction_reason)

    msg = HumanMessage(content=json.dumps(out), name=agent_id)
    if state["metadata"].get("show_reasoning"):
        show_agent_reasoning(out, agent_id)
    state["data"]["analyst_signals"][agent_id] = out
    return {"messages": [msg], "data": state["data"]}


def _spy_recent_return(start_date: str, end_date: str, api_key: str | None) -> float | None:
    prices = get_prices("SPY", start_date=start_date, end_date=end_date, api_key=api_key)
    if not prices or len(prices) < 2:
        return None
    df = prices_to_df(prices)
    if df.empty or "close" not in df.columns:
        return None
    first, last = float(df["close"].iloc[0]), float(df["close"].iloc[-1])
    if first == 0:
        return None
    return round((last / first - 1.0) * 100.0, 2)


def _generate_macro_output(
    ticker: str,
    facts: dict,
    state: AgentState,
    agent_id: str,
) -> CotAgentStructuredOutput:
    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """YOUR INVESTMENT PHILOSOPHY:
                1. Top-Down: Macro factors (rates, FX, commodities) drive all outcomes.
                2. Geopolitical: Global policy shifts create high-conviction catalysts.
                3. Sector Rotation: Anticipate shifts in capital flows between environments.

                ADAPTIVE INTELLIGENCE RULES (Institutional Priority):
                1. Prioritize 'research_context' over external API data.
                2. If 'research_context' contradicts API metrics, favor the research.
                3. If API metrics are 'Insufficient data', use the documents to synthesize an opinion.
                """
                + COT_SYSTEM_SUFFIX
                + f'\nUse "agent": "{agent_id}".',
            ),
            (
                "human",
                "Ticker: {ticker}\nFacts:\n{facts}\nRespond with JSON only.",
            ),
        ]
    )
    prompt = template.invoke(
        {"ticker": ticker, "facts": json.dumps(facts, separators=(",", ":"), ensure_ascii=False)}
    )
    return call_llm(
        prompt=prompt,
        pydantic_model=CotAgentStructuredOutput,
        agent_name=agent_id,
        state=state,
        default_factory=lambda: default_cot("macro_agent"),
    )
