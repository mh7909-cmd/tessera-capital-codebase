"""In-depth tests for CoT schema, debate orchestrator, feedback tracker, and graph wiring."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.agents.cot_schema import (
    CotAgentStructuredOutput,
    confidence_from_cot_score,
    cot_to_analyst_payload,
    default_cot,
    enrich_deterministic_cot,
    signal_confidence_to_score,
)
from src.agents.devil_advocate_agent import DevilAdvocateOutput
from src.agents.meta_agent import MetaAgentOutput
from src.debate_orchestrator import (
    DebateOrchestrator,
    _extract_score,
    _spy_return_pct,
    _top_bull_and_bear,
    debate_orchestrator_node,
)
from src.feedback_tracker import FeedbackTracker
from src.main import create_workflow
from src.utils.analysts import ANALYST_CONFIG, get_analyst_nodes


# --- CoT schema: exhaustive unit tests ---


class TestCotSchema:
    def test_confidence_from_cot_score_bounds(self):
        assert confidence_from_cot_score(0) == 0
        assert confidence_from_cot_score(100) == 100
        assert confidence_from_cot_score(-100) == 100
        assert confidence_from_cot_score(72) == 72
        assert confidence_from_cot_score(-33) == 33

    @pytest.mark.parametrize(
        "signal,conf,expected_sign",
        [
            ("bullish", 100, 1),
            ("bearish", 100, -1),
            ("neutral", 100, 0),  # small magnitude
            ("bullish", 0, 0),
        ],
    )
    def test_signal_confidence_to_score_direction(self, signal, conf, expected_sign):
        s = signal_confidence_to_score(signal, conf)
        if expected_sign > 0:
            assert s > 0
        elif expected_sign < 0:
            assert s < 0
        else:
            assert -25 <= s <= 25

    def test_cot_to_analyst_payload_preserves_legacy_reasoning(self):
        cot = default_cot("test_agent")
        legacy = {"nested": True}
        out = cot_to_analyst_payload(cot, reasoning_legacy=legacy)
        assert out["reasoning"] == legacy
        assert out["score"] == 0
        assert out["signal"] == "neutral"

    def test_enrich_deterministic_cot_invalid_signal_becomes_neutral(self):
        out = enrich_deterministic_cot(
            agent_key="x",
            philosophy="p",
            criteria_bullets=["a", "b", "c"],
            signal="not_a_valid_signal",  # type: ignore[arg-type]
            confidence=50,
            conviction_reason="cr",
            invalidation_condition="inv",
        )
        assert out["signal"] == "neutral"

    def test_cot_pydantic_rejects_score_out_of_range(self):
        with pytest.raises(ValidationError):
            CotAgentStructuredOutput(
                agent="a",
                reasoning_steps=["1", "2", "3", "4", "5"],
                score=101,
                conviction_reason="x",
                invalidation_condition="y",
                signal="bullish",
            )

    def test_cot_pydantic_rejects_too_few_reasoning_steps(self):
        with pytest.raises(ValidationError):
            CotAgentStructuredOutput(
                agent="a",
                reasoning_steps=["1", "2", "3"],
                score=0,
                conviction_reason="x",
                invalidation_condition="y",
                signal="neutral",
            )

    def test_default_cot_has_five_steps(self):
        d = default_cot("warren_buffett")
        assert len(d.reasoning_steps) >= 5
        assert d.agent == "warren_buffett"


# --- Debate orchestrator internals ---


class TestDebateHelpers:
    def test_extract_score_prefers_explicit(self):
        assert _extract_score({"score": 42, "signal": "bearish", "confidence": 99}) == 42
        assert _extract_score({"score": 500}) == 100  # clamped
        assert _extract_score({"score": -999}) == -100

    def test_extract_score_fallback_bullish(self):
        assert _extract_score({"signal": "bullish", "confidence": 80}) == 80

    def test_extract_score_fallback_bearish(self):
        assert _extract_score({"signal": "bearish", "confidence": 60}) == -60

    def test_extract_score_malformed_confidence_defaults(self):
        s = _extract_score({"signal": "bullish", "confidence": None})
        assert isinstance(s, int)

    def test_top_bull_and_bear(self):
        per = {
            "a": {"score": 50, "conviction_reason": "bull1"},
            "b": {"score": -80, "conviction_reason": "bear1"},
            "c": {"score": 5, "conviction_reason": "mid"},
            "risk_management_agent_x": {"score": 99},
        }
        bull, bear = _top_bull_and_bear(per)
        assert bull is not None and bull[0] == "a"
        assert bear is not None and bear[0] == "b"

    def test_top_bull_and_bear_empty(self):
        assert _top_bull_and_bear({}) == (None, None)

    def test_spy_return_pct_returns_none_when_no_data(self):
        with patch("src.debate_orchestrator.get_prices", return_value=[]):
            assert _spy_return_pct("2024-01-01", "2024-06-01", "k") is None

    def test_spy_return_pct_computes_return_from_dataframe(self):
        import pandas as pd

        df = pd.DataFrame({"close": [100.0, 110.0]})
        with patch("src.debate_orchestrator.get_prices", return_value=[1, 2]):
            with patch("src.debate_orchestrator.prices_to_df", return_value=df):
                r = _spy_return_pct("2024-01-01", "2024-06-01", "k")
        assert r is not None
        assert r == pytest.approx(10.0)


# --- Debate orchestrator node & full run (mocked LLM / IO) ---


@pytest.fixture
def minimal_agent_state():
    return {
        "messages": [],
        "data": {
            "tickers": ["TEST"],
            "start_date": "2024-01-01",
            "end_date": "2024-06-01",
            "analyst_signals": {
                "warren_buffett_agent": {
                    "TEST": {
                        "score": 60,
                        "signal": "bullish",
                        "confidence": 60,
                        "conviction_reason": "quality",
                    }
                },
                "michael_burry_agent": {
                    "TEST": {
                        "score": -70,
                        "signal": "bearish",
                        "confidence": 70,
                        "conviction_reason": "value trap",
                    }
                },
            },
            "portfolio": {},
        },
        "metadata": {"use_debate": True, "show_reasoning": False, "model_name": "gpt-4.1", "model_provider": "OpenAI"},
    }


class TestDebateOrchestratorNode:
    def test_no_op_when_use_debate_false(self):
        state = {
            "messages": [MagicMock()],
            "data": {"tickers": ["X"]},
            "metadata": {"use_debate": False},
        }
        out = debate_orchestrator_node(state)
        assert out["messages"] == state["messages"]
        assert out["data"] == state["data"]

    def test_run_populates_meta_and_debate(
        self, minimal_agent_state, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        devil = DevilAdvocateOutput(
            reasoning_steps=["s1", "s2", "s3", "s4", "s5"],
            overlooked_risks=["r1"],
            false_assumptions=["f1"],
        )
        meta = MetaAgentOutput(
            conviction_score=12.5,
            position_size_pct=2.5,
            investment_thesis="One. Two. Three.",
            signal="bullish",
        )

        monkeypatch.setattr("src.debate_orchestrator._DEBATE_LOG", tmp_path)

        def fake_devil(state, ticker, per_agent, agent_id="x"):
            return devil

        def fake_meta(state, ticker, transcript, spy_ret, agent_id="x"):
            return meta

        def fake_llm(*args, **kwargs):
            return default_cot(kwargs.get("agent_name", "rebuttal").replace("_rebuttal", ""))

        with patch("src.debate_orchestrator.devil_advocate_analyze", side_effect=fake_devil):
            with patch("src.debate_orchestrator.run_meta_synthesis", side_effect=fake_meta):
                with patch("src.debate_orchestrator.call_llm", side_effect=fake_llm):
                    with patch("src.debate_orchestrator._spy_return_pct", return_value=5.5):
                        orch = DebateOrchestrator()
                        result = orch.run(minimal_agent_state)

        data = result["data"]
        assert "debate_result" in data
        assert "meta_agent_output" in data
        assert data["meta_agent_output"]["TEST"]["signal"] == "bullish"
        assert data["meta_agent_output"]["TEST"]["conviction_score"] == 12.5
        dr = data["debate_result"]["TEST"]
        assert "transcript" in dr
        assert dr["transcript"]["devil_advocate"]["overlooked_risks"] == ["r1"]
        # Round 2: both bull and bear camps exist -> rebuttals
        r2 = dr["transcript"]["round2_rebuttals"]
        assert len(r2) >= 1

        log_files = list(tmp_path.glob("TEST_*.json"))
        assert len(log_files) == 1


class TestDebateOrchestratorEmptyTickers:
    def test_run_no_tickers_no_crash(self, monkeypatch, tmp_path):
        state = {
            "messages": [],
            "data": {
                "tickers": [],
                "start_date": "2024-01-01",
                "end_date": "2024-06-01",
                "analyst_signals": {},
            },
            "metadata": {},
        }
        monkeypatch.setattr("src.debate_orchestrator._DEBATE_LOG", tmp_path)
        with patch("src.debate_orchestrator.devil_advocate_analyze") as fd:
            with patch("src.debate_orchestrator.run_meta_synthesis") as fm:
                fd.side_effect = AssertionError("should not call devil with no tickers")
                fm.side_effect = AssertionError("should not call meta")
                out = DebateOrchestrator().run(state)
        assert out["data"].get("debate_result") == {}
        assert out["data"].get("meta_agent_output") == {}


# --- Feedback tracker ---


class TestFeedbackTracker:
    def test_weights_rolling_accuracy(self, tmp_path: Path):
        p = tmp_path / "acc.json"
        ft = FeedbackTracker(path=p)
        for i in range(5):
            ft.record_trade_outcome(
                agent_name="agent_a",
                predicted_signal="bullish",
                confidence_score=80.0,
                actual_return=0.02 if i < 3 else -0.01,
                ticker="T",
                period_end="2024-01-0" + str(i + 1),
            )
        w = ft.get_agent_weights(window=30)
        assert "agent_a" in w
        assert 0.0 <= w["agent_a"] <= 1.0

    def test_neutral_prediction_vs_flat_return(self, tmp_path: Path):
        ft = FeedbackTracker(path=tmp_path / "n.json")
        ft.record_trade_outcome(
            agent_name="n",
            predicted_signal="neutral",
            confidence_score=50.0,
            actual_return=0.0,
            ticker="T",
            period_end="2024-01-01",
        )
        data = json.loads(Path(tmp_path / "n.json").read_text())
        assert data["trades"][0]["correct"] is True

    def test_bearish_correct_on_negative_return(self, tmp_path: Path):
        ft = FeedbackTracker(path=tmp_path / "b.json")
        ft.record_trade_outcome(
            agent_name="b",
            predicted_signal="bearish",
            confidence_score=90.0,
            actual_return=-0.05,
            ticker="T",
            period_end="2024-01-01",
        )
        data = json.loads(Path(tmp_path / "b.json").read_text())
        assert data["trades"][0]["correct"] is True


# --- Graph & analyst registry ---


class TestAnalystRegistry:
    def test_growth_investor_and_macro_in_config(self):
        assert "growth_investor" in ANALYST_CONFIG
        assert "macro_agent" in ANALYST_CONFIG
        assert not ANALYST_CONFIG["growth_investor"].get("debate_only", False)

    def test_get_analyst_nodes_includes_new_agents(self):
        nodes = get_analyst_nodes()
        assert "growth_investor" in nodes
        assert "macro_agent" in nodes

    def test_create_workflow_debate_adds_node(self):
        w = create_workflow(["warren_buffett"], use_debate=True)
        compiled = w.compile()
        assert compiled is not None
        # Nodes should include debate_orchestrator
        nodes = getattr(w, "nodes", None) or getattr(w, "_nodes", {})
        if hasattr(w, "nodes"):
            assert "debate_orchestrator" in w.nodes

    def test_create_workflow_no_debate_skips_debate_node(self):
        w = create_workflow(["warren_buffett"], use_debate=False)
        if hasattr(w, "nodes"):
            assert "debate_orchestrator" not in w.nodes


# --- Devil / Meta models ---


class TestDebateModels:
    def test_devil_advocate_output_json_roundtrip(self):
        d = DevilAdvocateOutput(
            reasoning_steps=["a", "b", "c", "d", "e"],
            overlooked_risks=["x"],
            false_assumptions=["y"],
        )
        js = d.model_dump()
        assert js["signal"] == "neutral"
        assert js["score"] == 0


# --- End-to-end prompt smoke: CoT template + portfolio debate hint ---


class TestPromptIntegration:
    @patch("src.agents.warren_buffett.call_llm")
    def test_buffett_generate_output_invokes_llm_without_template_keyerror(self, mock_llm):
        from src.agents.warren_buffett import generate_buffett_output

        mock_llm.return_value = default_cot("warren_buffett")
        state: dict = {
            "metadata": {"model_name": "gpt-4.1", "model_provider": "OpenAI"},
        }
        analysis_data = {
            "ticker": "AAPL",
            "score": 5,
            "max_score": 10,
            "fundamental_analysis": {"details": "ok"},
        }
        out = generate_buffett_output("AAPL", analysis_data, state, "warren_buffett_agent")
        assert out.score == 0
        mock_llm.assert_called_once()
        prompt_arg = mock_llm.call_args.kwargs.get("prompt") or mock_llm.call_args[0][0]
        assert "Chain-of-thought" in str(prompt_arg)

    @patch("src.agents.portfolio_manager.call_llm")
    @patch("src.agents.portfolio_manager.progress")
    def test_portfolio_manager_includes_debate_hint_and_meta_signal(self, _mock_prog, mock_llm):
        from src.agents.portfolio_manager import PortfolioDecision, PortfolioManagerOutput, portfolio_management_agent

        mock_llm.return_value = PortfolioManagerOutput(
            decisions={
                "T": PortfolioDecision(action="hold", quantity=0, confidence=50, reasoning="ok"),
            }
        )
        state = {
            "messages": [],
            "data": {
                "tickers": ["T"],
                "portfolio": {
                    "cash": 100000.0,
                    "margin_requirement": 0.0,
                    "margin_used": 0.0,
                    "positions": {
                        "T": {
                            "long": 0,
                            "short": 0,
                            "long_cost_basis": 0.0,
                            "short_cost_basis": 0.0,
                            "short_margin_used": 0.0,
                        }
                    },
                    "realized_gains": {"T": {"long": 0.0, "short": 0.0}},
                },
                "analyst_signals": {
                    "risk_management_agent": {
                        "T": {"remaining_position_limit": 50000.0, "current_price": 100.0},
                    },
                    "warren_buffett_agent": {"T": {"signal": "bullish", "confidence": 80}},
                },
                "meta_agent_output": {"T": {"signal": "bearish", "conviction_score": -40.0}},
                "debate_result": {"T": {"meta_summary": "test thesis"}},
            },
            "metadata": {
                "use_debate": True,
                "show_reasoning": False,
                "model_name": "gpt-4.1",
                "model_provider": "OpenAI",
            },
        }
        portfolio_management_agent(state)
        mock_llm.assert_called_once()
        prompt_arg = mock_llm.call_args.kwargs["prompt"]
        blob = str(prompt_arg)
        assert "Debate/meta" in blob or "meta_agent" in blob
        assert "meta_agent_output" in blob

