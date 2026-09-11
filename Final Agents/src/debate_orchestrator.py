"""Multi-round adversarial debate orchestrator: devil's advocate, rebuttals, meta synthesis."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agents.cot_schema import COT_SYSTEM_SUFFIX, CotAgentStructuredOutput, default_cot
from src.agents.devil_advocate_agent import DevilAdvocateOutput, devil_advocate_analyze
from src.agents.meta_agent import MetaAgentOutput, run_meta_synthesis
from src.graph.state import AgentState
from src.tools.api import get_prices, prices_to_df
from src.utils.api_key import get_api_key_from_state
from src.utils.llm import call_llm
from src.utils.progress import progress

_DEBATE_LOG = Path(__file__).resolve().parent.parent / "debate_logs"
_RISK_PREFIX = "risk_management_agent"


def _spy_return_pct(start_date: str, end_date: str, api_key: str | None) -> float | None:
    prices = get_prices("SPY", start_date=start_date, end_date=end_date, api_key=api_key)
    if not prices or len(prices) < 2:
        return None
    df = prices_to_df(prices)
    if df.empty or "close" not in df.columns:
        return None
    a, b = float(df["close"].iloc[0]), float(df["close"].iloc[-1])
    if a == 0:
        return None
    return round((b / a - 1.0) * 100.0, 4)


def _extract_score(payload: dict[str, Any]) -> int:
    if "score" in payload and payload["score"] is not None:
        try:
            return max(-100, min(100, int(payload["score"])))
        except (TypeError, ValueError):
            pass
    sig = payload.get("signal")
    conf = payload.get("confidence")
    try:
        c = float(conf)
    except (TypeError, ValueError):
        c = 50.0
    c = max(0.0, min(100.0, c))
    if sig == "bullish":
        return int(round(c))
    if sig == "bearish":
        return -int(round(c))
    return int(round((c / 100.0) * 25)) - 12


def _top_bull_and_bear(
    per_agent: dict[str, dict[str, Any]],
) -> tuple[tuple[str, str] | None, tuple[str, str] | None]:
    """Return (agent_id, conviction_reason) for strongest bull and bear by score."""
    best_bull: tuple[int, str, str] | None = None
    best_bear: tuple[int, str, str] | None = None
    for aid, p in per_agent.items():
        if aid.startswith(_RISK_PREFIX) or aid == "meta_agent":
            continue
        sc = _extract_score(p)
        reason = p.get("conviction_reason") or p.get("reasoning")
        if isinstance(reason, dict):
            reason = json.dumps(reason, default=str)[:500]
        reason = str(reason or "")[:2000]
        if sc > 20:
            if best_bull is None or sc > best_bull[0]:
                best_bull = (sc, aid, reason)
        if sc < -20:
            if best_bear is None or sc < best_bear[0]:
                best_bear = (sc, aid, reason)
    bull = (best_bull[1], best_bull[2]) if best_bull else None
    bear = (best_bear[1], best_bear[2]) if best_bear else None
    return bull, bear


class DebateOrchestrator:
    """
    Round 1 uses analyst outputs already in ``state['data']['analyst_signals']``.
    Runs devil's advocate, optional round-2 rebuttals, then meta synthesis.
    Persists JSON logs under ``debate_logs/{ticker}_{date}.json``.
    """

    def __init__(self) -> None:
        pass

    def run(self, state: AgentState) -> dict[str, Any]:
        """Populate ``debate_result``, ``meta_agent_output`` on ``state['data']``."""
        data = state["data"]
        tickers: list[str] = data.get("tickers", [])
        start_date = data["start_date"]
        end_date = data["end_date"]
        api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")
        spy_ret = _spy_return_pct(start_date, end_date, api_key)

        analyst_signals: dict[str, Any] = data.get("analyst_signals", {})
        debate_result: dict[str, Any] = {}
        meta_out: dict[str, Any] = {}

        for ticker in tickers:
            progress.update_status("debate_orchestrator", ticker, "Collecting agent outputs")
            per_agent: dict[str, Any] = {}
            for aid, block in analyst_signals.items():
                if aid.startswith(_RISK_PREFIX):
                    continue
                if isinstance(block, dict) and ticker in block:
                    per_agent[aid] = block[ticker]

            devil: DevilAdvocateOutput = devil_advocate_analyze(state, ticker, per_agent)
            import time
            time.sleep(2) # Allow narration of devil's advocate entry
            bull, bear = _top_bull_and_bear(per_agent)

            bulls = [a for a, p in per_agent.items() if _extract_score(p) > 20]
            bears = [a for a, p in per_agent.items() if _extract_score(p) < -20]

            round2: dict[str, Any] = {}
            tasks: list[tuple[str, str, str, str]] = []
            # (agent_id, counter_text, stance)
            if bear and bulls:
                for b in bulls:
                    tasks.append((b, bear[1], "bull_receives_top_bear"))
            if bull and bears:
                for b in bears:
                    tasks.append((b, bull[1], "bear_receives_top_bull"))

            def _one_rebuttal(agent_id: str, counter: str, tag: str) -> tuple[str, Any]:
                prior = per_agent.get(agent_id, {})
                template = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            f"You are continuing as agent `{agent_id}`. "
                            f"Counter-argument ({tag}): respond and update your view.\n"
                            + COT_SYSTEM_SUFFIX
                            + f'\nUse "agent": "{agent_id}_rebuttal".',
                        ),
                        (
                            "human",
                            "Your prior output:\n{prior}\n\nCounter-argument:\n{counter}\n"
                            "Respond with JSON only.",
                        ),
                    ]
                )
                prompt = template.invoke(
                    {
                        "prior": json.dumps(prior, default=str)[:8000],
                        "counter": counter[:8000],
                    }
                )

                def _fb() -> CotAgentStructuredOutput:
                    return default_cot(f"{agent_id}_rebuttal")

                cot = call_llm(
                    prompt=prompt,
                    pydantic_model=CotAgentStructuredOutput,
                    agent_name=f"{agent_id}_rebuttal",
                    state=state,
                    default_factory=_fb,
                )
                return agent_id, {"tag": tag, "rebuttal": cot.model_dump()}

            if tasks:
                with ThreadPoolExecutor(max_workers=min(8, max(1, len(tasks)))) as ex:
                    futs = [ex.submit(_one_rebuttal, a, c, t) for a, c, t in tasks]
                    for fut in as_completed(futs):
                        aid, payload = fut.result()
                        round2[aid] = payload

            transcript: dict[str, Any] = {
                "round1": per_agent,
                "devil_advocate": devil.model_dump(),
                "top_bull_argument": {"agent": bull[0], "text": bull[1]} if bull else None,
                "top_bear_argument": {"agent": bear[0], "text": bear[1]} if bear else None,
                "round2_rebuttals": round2,
                "spy_recent_return_pct": spy_ret,
            }

            time.sleep(3) # Deliberate pause before meta-synthesis
            meta: MetaAgentOutput = run_meta_synthesis(
                state,
                ticker,
                transcript,
                spy_ret,
            )
            meta_out[ticker] = meta.model_dump()

            debate_result[ticker] = {
                "transcript": transcript,
                "meta_summary": meta.investment_thesis,
                "conviction_score": meta.conviction_score,
                "position_size_pct": meta.position_size_pct,
                "signal": meta.signal,
            }

            self._write_log(ticker, end_date, debate_result[ticker])

        data["debate_result"] = debate_result
        data["meta_agent_output"] = meta_out

        msg = HumanMessage(
            content=json.dumps({"debate_result": debate_result, "meta_agent_output": meta_out}),
            name="debate_orchestrator",
        )
        progress.update_status("debate_orchestrator", None, "Done")
        return {"messages": state["messages"] + [msg], "data": data}

    @staticmethod
    def _write_log(ticker: str, date: str, payload: dict[str, Any]) -> None:
        _DEBATE_LOG.mkdir(parents=True, exist_ok=True)
        path = _DEBATE_LOG / f"{ticker}_{date}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"ticker": ticker, "date": date, "logged_at": datetime.utcnow().isoformat() + "Z", **payload},
                f,
                indent=2,
            )


def debate_orchestrator_node(state: AgentState):
    """LangGraph node: no-op if ``use_debate`` is false."""
    if not state.get("metadata", {}).get("use_debate"):
        return {"messages": state["messages"], "data": state["data"]}
    orch = DebateOrchestrator()
    return orch.run(state)
