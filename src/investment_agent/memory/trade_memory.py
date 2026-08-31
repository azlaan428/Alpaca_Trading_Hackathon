"""Trade Memory — Structured Experience Logging and Retrieval for X Quant X.

WHAT
====
Provides a JSON-backed trade memory system that records structured trading
experiences and enables retrieval of similar historical situations.

WHY
===
The architecture produces deterministic analytical outputs, but without memory
it cannot learn from past trades. This module provides:

1. Structured experience logging (TradeExperience)
2. Similarity-based retrieval of historical situations
3. Outcome tracking and P&L computation
4. Integration with agent reputation for feedback

HOW
===
- Records every completed trade as a TradeExperience dataclass
- Persists to JSON file for durability
- Computes similarity between current and historical situations
- Returns ranked historical contexts for decision support

TradeExperience Schema
======================
{
    "timestamp": ISO-8601,
    "symbol": str,
    "regime": str (R01-R12),
    "regime_probabilities": Dict[str, float],
    "agent_signals": Dict[str, float],
    "ensemble_signal": float,
    "disagreement": float,
    "effective_confidence": float,
    "kalman_gain": float,
    "kalman_price": float,
    "kalman_trend": float,
    "capital_gate_verdict": str,
    "effective_cap": float,
    "state_charges": Dict[str, float],
    "position_action": str,
    "quantity": float,
    "confidence": float,
    "expected_outcome": str,
    "realized_outcome": str,
    "pnl": float,
    "lesson": str
}

Similarity Metric
=================
Uses weighted Euclidean distance in feature space:
- Regime match (highest weight)
- Ensemble signal similarity
- Disagreement similarity
- Kalman state similarity
- Capital gate similarity

Architectural Role
==================
Experience layer. Sits between Capital Gate and Execution, recording outcomes
and providing historical context for future decisions.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default memory file location
DEFAULT_MEMORY_FILE: str = "trade_memory.json"

# Maximum number of experiences to retain per symbol
MAX_MEMORY_PER_SYMBOL: int = 1000

# Similarity feature weights
_SIMILARITY_WEIGHTS = {
    "regime": 3.0,
    "ensemble_signal": 2.0,
    "disagreement": 1.5,
    "kalman_gain": 1.5,
    "effective_cap": 1.0,
    "confidence": 1.0,
}


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TradeExperience:
    """Immutable structured trading experience record.

    Attributes
    ----------
    timestamp : datetime
        When the trade decision was made.
    symbol : str
        Trading symbol (e.g., "AAPL", "TSLA").
    regime : str
        Active regime at time of decision (R01-R12).
    regime_probabilities : Dict[str, float]
        HMM posterior probabilities over all regimes.
    agent_signals : Dict[str, float]
        Individual agent signal outputs.
    ensemble_signal : float
        Weighted ensemble aggregate signal.
    disagreement : float
        Ensemble disagreement metric.
    effective_confidence : float
        Ensemble effective confidence.
    kalman_gain : float
        Investment Kalman gain K_t.
    kalman_price : float
        Kalman estimated price at decision time.
    kalman_trend : float
        Kalman trend estimate at decision time.
    capital_gate_verdict : str
        Capital gate verdict (ALLOW, REDUCE, BLOCK, FLATTEN).
    effective_cap : float
        Effective capital deployment cap.
    state_charges : Dict[str, float]
        Seven-state charge values at decision time.
    position_action : str
        Action taken (BUY, SELL, HOLD, etc.).
    quantity : float
        Position quantity (shares or contracts).
    confidence : float
        Decision confidence in [0.0, 1.0].
    expected_outcome : str
        Expected outcome description.
    realized_outcome : str
        Actual realized outcome (filled after trade completion).
    pnl : float
        Realized profit/loss.
    lesson : str
        Extracted lesson/reflection from this experience.
    """

    timestamp: datetime
    symbol: str
    regime: str
    regime_probabilities: Dict[str, float]
    agent_signals: Dict[str, float]
    ensemble_signal: float
    disagreement: float
    effective_confidence: float
    kalman_gain: float
    kalman_price: float
    kalman_trend: float
    capital_gate_verdict: str
    effective_cap: float
    state_charges: Dict[str, float]
    position_action: str
    quantity: float
    confidence: float
    expected_outcome: str
    realized_outcome: str
    pnl: float
    lesson: str


@dataclass(frozen=True)
class SimilarExperience:
    """A historically similar experience with similarity score.

    Attributes
    ----------
    experience : TradeExperience
        The historical trade experience.
    similarity_score : float
        Similarity score in [0.0, 1.0], higher is more similar.
    match_reasons : List[str]
        Human-readable explanations of why this experience is similar.
    """

    experience: TradeExperience
    similarity_score: float
    match_reasons: List[str]


# ---------------------------------------------------------------------------
# Memory Store
# ---------------------------------------------------------------------------

class TradeMemory:
    """Persistent trade memory with similarity-based retrieval.

    Stores TradeExperience records in JSON format and provides methods
    for logging new experiences and finding similar historical situations.
    """

    def __init__(self, memory_file: str = DEFAULT_MEMORY_FILE) -> None:
        """Initialize trade memory.

        Parameters
        ----------
        memory_file : str
            Path to JSON memory file.
        """
        self._memory_file = memory_file
        self._experiences: List[TradeExperience] = []
        self._load()

    def _load(self) -> None:
        """Load experiences from disk."""
        if not os.path.exists(self._memory_file):
            self._experiences = []
            return

        try:
            with open(self._memory_file, "r") as f:
                raw = json.load(f)
            self._experiences = [
                self._deserialize(r) for r in raw if self._is_valid_experience(r)
            ]
        except Exception:
            self._experiences = []

    def _save(self) -> None:
        """Save experiences to disk."""
        raw = [self._serialize(e) for e in self._experiences]
        with open(self._memory_file, "w") as f:
            json.dump(raw, f, indent=2, default=str)

    def _serialize(self, exp: TradeExperience) -> Dict[str, Any]:
        """Convert TradeExperience to JSON-serializable dict."""
        return {
            "timestamp": exp.timestamp.isoformat(),
            "symbol": exp.symbol,
            "regime": exp.regime,
            "regime_probabilities": exp.regime_probabilities,
            "agent_signals": exp.agent_signals,
            "ensemble_signal": exp.ensemble_signal,
            "disagreement": exp.disagreement,
            "effective_confidence": exp.effective_confidence,
            "kalman_gain": exp.kalman_gain,
            "kalman_price": exp.kalman_price,
            "kalman_trend": exp.kalman_trend,
            "capital_gate_verdict": exp.capital_gate_verdict,
            "effective_cap": exp.effective_cap,
            "state_charges": exp.state_charges,
            "position_action": exp.position_action,
            "quantity": exp.quantity,
            "confidence": exp.confidence,
            "expected_outcome": exp.expected_outcome,
            "realized_outcome": exp.realized_outcome,
            "pnl": exp.pnl,
            "lesson": exp.lesson,
        }

    def _deserialize(self, raw: Dict[str, Any]) -> TradeExperience:
        """Convert JSON dict to TradeExperience."""
        return TradeExperience(
            timestamp=datetime.fromisoformat(raw["timestamp"]),
            symbol=raw["symbol"],
            regime=raw["regime"],
            regime_probabilities=raw.get("regime_probabilities", {}),
            agent_signals=raw.get("agent_signals", {}),
            ensemble_signal=raw.get("ensemble_signal", 0.0),
            disagreement=raw.get("disagreement", 0.0),
            effective_confidence=raw.get("effective_confidence", 0.0),
            kalman_gain=raw.get("kalman_gain", 0.0),
            kalman_price=raw.get("kalman_price", 0.0),
            kalman_trend=raw.get("kalman_trend", 0.0),
            capital_gate_verdict=raw.get("capital_gate_verdict", "UNKNOWN"),
            effective_cap=raw.get("effective_cap", 0.0),
            state_charges=raw.get("state_charges", {}),
            position_action=raw.get("position_action", "HOLD"),
            quantity=raw.get("quantity", 0.0),
            confidence=raw.get("confidence", 0.0),
            expected_outcome=raw.get("expected_outcome", ""),
            realized_outcome=raw.get("realized_outcome", ""),
            pnl=raw.get("pnl", 0.0),
            lesson=raw.get("lesson", ""),
        )

    def _is_valid_experience(self, raw: Dict[str, Any]) -> bool:
        """Validate raw dict has required fields."""
        required = ["timestamp", "symbol", "regime", "position_action"]
        return all(field in raw for field in required)

    def log_experience(self, experience: TradeExperience) -> None:
        """Record a new trade experience.

        Parameters
        ----------
        experience : TradeExperience
            The experience to record.
        """
        self._experiences.append(experience)
        self._enforce_limits()
        self._save()

    def _enforce_limits(self) -> None:
        """Enforce per-symbol memory limits."""
        by_symbol: Dict[str, List[TradeExperience]] = {}
        for exp in self._experiences:
            by_symbol.setdefault(exp.symbol, []).append(exp)

        self._experiences = []
        for symbol, exps in by_symbol.items():
            exps.sort(key=lambda e: e.timestamp)
            self._experiences.extend(exps[-MAX_MEMORY_PER_SYMBOL:])

    def find_similar(
        self,
        current: TradeExperience,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> List[SimilarExperience]:
        """Find historically similar experiences.

        Parameters
        ----------
        current : TradeExperience
            Current situation to match against.
        top_k : int
            Maximum number of similar experiences to return.
        min_similarity : float
            Minimum similarity score threshold.

        Returns
        -------
        List[SimilarExperience]
            Ranked list of similar historical experiences.
        """
        scored: List[SimilarExperience] = []

        for hist in self._experiences:
            score, reasons = self._compute_similarity(current, hist)
            if score >= min_similarity:
                scored.append(SimilarExperience(
                    experience=hist,
                    similarity_score=score,
                    match_reasons=reasons,
                ))

        scored.sort(key=lambda s: s.similarity_score, reverse=True)
        return scored[:top_k]

    def _compute_similarity(
        self,
        current: TradeExperience,
        historical: TradeExperience,
    ) -> Tuple[float, List[str]]:
        """Compute similarity between current and historical experiences.

        Returns
        -------
        Tuple[float, List[str]]
            Similarity score in [0.0, 1.0] and list of match reasons.
        """
        reasons: List[str] = []
        total_weight = 0.0
        weighted_score = 0.0

        # Regime match (highest weight)
        if current.regime == historical.regime:
            weighted_score += _SIMILARITY_WEIGHTS["regime"]
            reasons.append(f"Same regime ({current.regime})")
        else:
            # Partial credit for adjacent regimes
            current_num = int(current.regime[1:])
            hist_num = int(historical.regime[1:])
            if abs(current_num - hist_num) <= 1:
                weighted_score += _SIMILARITY_WEIGHTS["regime"] * 0.5
                reasons.append(f"Adjacent regime ({current.regime} vs {historical.regime})")
        total_weight += _SIMILARITY_WEIGHTS["regime"]

        # Ensemble signal similarity
        sig_diff = abs(current.ensemble_signal - historical.ensemble_signal)
        sig_sim = max(0.0, 1.0 - sig_diff)
        weighted_score += _SIMILARITY_WEIGHTS["ensemble_signal"] * sig_sim
        total_weight += _SIMILARITY_WEIGHTS["ensemble_signal"]
        if sig_sim > 0.7:
            reasons.append(f"Similar ensemble signal ({sig_sim:.2f})")

        # Disagreement similarity
        disag_diff = abs(current.disagreement - historical.disagreement)
        disag_sim = max(0.0, 1.0 - disag_diff)
        weighted_score += _SIMILARITY_WEIGHTS["disagreement"] * disag_sim
        total_weight += _SIMILARITY_WEIGHTS["disagreement"]

        # Kalman gain similarity
        gain_diff = abs(current.kalman_gain - historical.kalman_gain)
        gain_sim = max(0.0, 1.0 - gain_diff)
        weighted_score += _SIMILARITY_WEIGHTS["kalman_gain"] * gain_sim
        total_weight += _SIMILARITY_WEIGHTS["kalman_gain"]

        # Effective cap similarity
        cap_diff = abs(current.effective_cap - historical.effective_cap)
        cap_sim = max(0.0, 1.0 - cap_diff)
        weighted_score += _SIMILARITY_WEIGHTS["effective_cap"] * cap_sim
        total_weight += _SIMILARITY_WEIGHTS["effective_cap"]

        # Confidence similarity
        conf_diff = abs(current.confidence - historical.confidence)
        conf_sim = max(0.0, 1.0 - conf_diff)
        weighted_score += _SIMILARITY_WEIGHTS["confidence"] * conf_sim
        total_weight += _SIMILARITY_WEIGHTS["confidence"]

        score = weighted_score / total_weight if total_weight > 0 else 0.0
        return score, reasons

    def get_history(self, symbol: Optional[str] = None) -> List[TradeExperience]:
        """Return experience history, optionally filtered by symbol.

        Parameters
        ----------
        symbol : Optional[str]
            If provided, return only experiences for this symbol.

        Returns
        -------
        List[TradeExperience]
            Experience history.
        """
        if symbol is None:
            return list(self._experiences)
        return [e for e in self._experiences if e.symbol == symbol]

    def get_performance_summary(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Compute performance summary from experience history.

        Parameters
        ----------
        symbol : Optional[str]
            If provided, summarize only this symbol.

        Returns
        -------
        Dict[str, Any]
            Performance summary with win rate, avg P&L, etc.
        """
        exps = self.get_history(symbol)
        if not exps:
            return {"count": 0}

        pnls = [e.pnl for e in exps]
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)

        return {
            "count": len(exps),
            "win_rate": wins / len(exps) if exps else 0.0,
            "avg_pnl": sum(pnls) / len(pnls) if pnls else 0.0,
            "total_pnl": sum(pnls),
            "wins": wins,
            "losses": losses,
            "best_trade": max(pnls) if pnls else 0.0,
            "worst_trade": min(pnls) if pnls else 0.0,
        }

    def clear(self) -> None:
        """Clear all experiences from memory."""
        self._experiences = []
        self._save()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "TradeExperience",
    "SimilarExperience",
    "TradeMemory",
    "DEFAULT_MEMORY_FILE",
]
