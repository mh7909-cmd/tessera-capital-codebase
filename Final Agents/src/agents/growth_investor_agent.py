"""Secular growth analyst: innovation cycles, TAM, disruption, and multi-year CAGR.

Focus: TAM, disruption, 5-year revenue CAGR, R&D intensity, innovation proxies.
Emits chain-of-thought JSON aligned with `CotAgentStructuredOutput`.
"""

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
from src.tools.api import get_financial_metrics, get_market_cap, search_line_items
from src.utils.api_key import get_api_key_from_state
from src.utils.llm import call_llm
from src.utils.progress import progress


def secular_growth_analyst_agent(state: AgentState, agent_id: str = "secular_growth_analyst"):
    """Run growth-investor analysis for each ticker."""
    data = state["data"]
    end_date = data["end_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")
    out: dict[str, dict] = {}

    for ticker in tickers:
        progress.update_status(agent_id, ticker, "Fetching metrics")
        metrics = get_financial_metrics(ticker, end_date, period="annual", limit=8, api_key=api_key)
        line_items = search_line_items(
            ticker,
            [
                "revenue",
                "research_and_development",
                "operating_expense",
                "gross_margin",
                "operating_margin",
                "free_cash_flow",
            ],
            end_date,
            period="annual",
            limit=8,
            api_key=api_key,
        )
        market_cap = get_market_cap(ticker, end_date, api_key=api_key)

        facts = {
            "ticker": ticker,
            "market_cap": market_cap,
            "metrics_head": [m.model_dump() for m in (metrics or [])[:5]],
            "line_items_head": [li.model_dump() for li in (line_items or [])[:5]],
            "research_context": state["data"].get("research_context", "No external documents provided."),
        }
        progress.update_status(agent_id, ticker, "Generating growth investor thesis")
        cot = _generate_growth_investor_output(ticker, facts, state, agent_id)
        out[ticker] = cot_to_analyst_payload(cot)
        progress.update_status(agent_id, ticker, "Done", analysis=cot.conviction_reason)

    msg = HumanMessage(content=json.dumps(out), name=agent_id)
    if state["metadata"].get("show_reasoning"):
        show_agent_reasoning(out, agent_id)
    state["data"]["analyst_signals"][agent_id] = out
    return {"messages": [msg], "data": state["data"]}


def _generate_growth_investor_output(
    ticker: str,
    facts: dict,
    state: AgentState,
    agent_id: str,
) -> CotAgentStructuredOutput:
    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a secular growth analyst focused on multi-generational innovation cycles. "
                "YOUR INVESTMENT PHILOSOPHY:"
                "1. TAM Expansion: Massive total addressable markets."
                "2. Disruption: Unseating incumbents through technology."
                "3. R&D Intensity: High investment in the future."
                "4. Unit Economics: Multi-year CAGR potential."

                "ADAPTIVE INTELLIGENCE RULES (Institutional Priority):"
                "1. Prioritize 'research_context' over external API data."
                "2. If 'research_context' contradicts API metrics, favor the research."
                "3. If API metrics are 'Insufficient data', use the documents to synthesize an opinion.\n"
                + COT_SYSTEM_SUFFIX
                + '\nUse "agent": "secular_growth_analyst".',
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
        default_factory=lambda: default_cot("secular_growth_analyst"),
    )
