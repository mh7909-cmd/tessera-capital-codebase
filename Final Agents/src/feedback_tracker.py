"""Tracks per-agent prediction accuracy vs realized returns and exposes rolling weights."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from typing_extensions import Literal

Signal = Literal["bullish", "bearish", "neutral"]

_LOG_ROOT = Path(__file__).resolve().parent.parent / "feedback_logs"
_ACCURACY_PATH = _LOG_ROOT / "agent_accuracy.json"


class FeedbackTracker:
    """
    Append-only store of agent predictions vs outcomes; `get_agent_weights` returns
    rolling accuracy over the last 30 records per agent (default weight 1.0).
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _ACCURACY_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({"trades": []})

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"trades": []}
        with open(self._path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict[str, Any]) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def record_trade_outcome(
        self,
        *,
        agent_name: str,
        predicted_signal: Signal,
        confidence_score: float,
        actual_return: float,
        ticker: str,
        period_end: str,
    ) -> None:
        """Store one observation: whether directional signal matched realized return sign."""
        correct = self._is_correct(predicted_signal, actual_return)
        row = {
            "agent_name": agent_name,
            "predicted_signal": predicted_signal,
            "confidence_score": confidence_score,
            "actual_return": actual_return,
            "correct": correct,
            "ticker": ticker,
            "period_end": period_end,
            "recorded_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        data = self._read()
        data.setdefault("trades", []).append(row)
        self._write(data)

    @staticmethod
    def _is_correct(predicted_signal: Signal, actual_return: float) -> bool:
        if actual_return > 0:
            return predicted_signal == "bullish"
        if actual_return < 0:
            return predicted_signal == "bearish"
        return predicted_signal == "neutral"

    def get_agent_weights(self, window: int = 30) -> dict[str, float]:
        """
        Rolling accuracy (0..1) over the last `window` trades per agent.
        Agents with no history default to 1.0 so they are not zeroed out.
        """
        data = self._read()
        trades: list[dict[str, Any]] = data.get("trades", [])
        by_agent: dict[str, list[bool]] = {}
        for t in trades:
            name = t.get("agent_name")
            if not name:
                continue
            by_agent.setdefault(name, []).append(bool(t.get("correct")))

        weights: dict[str, float] = {}
        for name, flags in by_agent.items():
            recent = flags[-window:]
            if not recent:
                weights[name] = 1.0
            else:
                weights[name] = round(sum(1 for x in recent if x) / len(recent), 4)
        return weights
