"""Tests for trade memory and orchestrator."""

import math
import unittest
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np

from investment_agent.regimes.regime_detector import RegimeClassification
from investment_agent.regimes.regimes import VALID_REGIMES
from investment_agent.signals.ensemble_signal import AgentOutput, EnsembleAggregate, compute_ensemble_aggregate
from investment_agent.filters.kalman_filter import KalmanState
from investment_agent.capital.capital_gate import CapitalGateResult, RiskVerdict
from investment_agent.memory.trade_memory import (
    TradeExperience,
    SimilarExperience,
    TradeMemory,
    DEFAULT_MEMORY_FILE,
    MAX_MEMORY_PER_SYMBOL,
)
from investment_agent.orchestrator import (
    XQuantXOrchestrator,
    TradingDecision,
    CycleResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AGENT_IDS = [f"agent{i}" for i in range(1, 8)]


def make_agent_outputs(
    signals: List[float],
    confidences: List[float],
) -> List[AgentOutput]:
    """Create AgentOutput list."""
    return [
        AgentOutput(
            s=signals[i],
            c=confidences[i],
            u=0.0,
            d=0.0,
            p_plus=0.5 + signals[i] * 0.25,
            p_minus=0.5 - signals[i] * 0.25,
            delta_t=1.0,
            r=0.01,
            agent_id=AGENT_IDS[i],
        )
        for i in range(len(signals))
    ]


def make_kalman_state(**overrides) -> KalmanState:
    """Create KalmanState with defaults."""
    defaults = {
        "estimated_price": 100.0,
        "trend": 0.01,
        "uncertainty": 1.0,
        "trend_uncertainty": 0.1,
        "price_variance": 1.0,
        "trend_variance": 0.01,
        "innovation": 0.0,
        "kalman_gain_price": 0.5,
    }
    defaults.update(overrides)
    return KalmanState(**defaults)


def make_capital_gate_result(**overrides) -> CapitalGateResult:
    """Create CapitalGateResult with defaults."""
    defaults = {
        "verdict": RiskVerdict.ALLOW,
        "gating_factor": 0.8,
        "effective_cap": 0.5,
        "reduce_factor": 1.0,
        "state_charges": {},
        "state_gatings": {},
        "triggered_rules": (),
        "reason": "Test gate",
        "kalman_gain": 0.5,
    }
    defaults.update(overrides)
    return CapitalGateResult(**defaults)


def make_regime_classification(**overrides) -> RegimeClassification:
    """Create RegimeClassification with defaults."""
    defaults = {
        "regime": "R01",
        "confidence": 0.8,
        "timestamp": datetime.now(),
        "features": {"annualized_return": 0.1, "annualized_volatility": 0.2},
        "regime_affinity": {f"R{i:02d}": 1.0 / 12 for i in range(1, 13)},
    }
    defaults.update(overrides)
    return RegimeClassification(**defaults)


# ---------------------------------------------------------------------------
# Test TradeMemory
# ---------------------------------------------------------------------------

class TestTradeMemory(unittest.TestCase):
    """Test trade memory persistence and retrieval."""

    def setUp(self):
        """Create fresh memory for each test."""
        self.memory = TradeMemory(memory_file="test_memory.json")

    def tearDown(self):
        """Clean up test memory file."""
        import os
        if os.path.exists("test_memory.json"):
            os.remove("test_memory.json")

    def test_log_and_retrieve_experience(self):
        """Verify experience can be logged and retrieved."""
        exp = TradeExperience(
            timestamp=datetime.now(),
            symbol="AAPL",
            regime="R01",
            regime_probabilities={"R01": 0.8},
            agent_signals={"agent1": 0.5},
            ensemble_signal=0.5,
            disagreement=0.2,
            effective_confidence=0.8,
            kalman_gain=0.5,
            kalman_price=100.0,
            kalman_trend=0.01,
            capital_gate_verdict="ALLOW",
            effective_cap=0.5,
            state_charges={"economic": 1.0},
            position_action="BUY",
            quantity=1.0,
            confidence=0.8,
            expected_outcome="Price up",
            realized_outcome="PENDING",
            pnl=0.0,
            lesson="",
        )
        self.memory.log_experience(exp)
        history = self.memory.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].symbol, "AAPL")

    def test_find_similar_experiences(self):
        """Verify similar experience retrieval."""
        # Log experience
        exp1 = TradeExperience(
            timestamp=datetime.now(),
            symbol="AAPL",
            regime="R01",
            regime_probabilities={"R01": 0.8},
            agent_signals={"agent1": 0.5},
            ensemble_signal=0.5,
            disagreement=0.2,
            effective_confidence=0.8,
            kalman_gain=0.5,
            kalman_price=100.0,
            kalman_trend=0.01,
            capital_gate_verdict="ALLOW",
            effective_cap=0.5,
            state_charges={"economic": 1.0},
            position_action="BUY",
            quantity=1.0,
            confidence=0.8,
            expected_outcome="Price up",
            realized_outcome="PENDING",
            pnl=0.0,
            lesson="",
        )
        self.memory.log_experience(exp1)

        # Create similar current experience
        current = TradeExperience(
            timestamp=datetime.now(),
            symbol="AAPL",
            regime="R01",
            regime_probabilities={"R01": 0.8},
            agent_signals={"agent1": 0.5},
            ensemble_signal=0.5,
            disagreement=0.2,
            effective_confidence=0.8,
            kalman_gain=0.5,
            kalman_price=100.0,
            kalman_trend=0.01,
            capital_gate_verdict="ALLOW",
            effective_cap=0.5,
            state_charges={"economic": 1.0},
            position_action="BUY",
            quantity=1.0,
            confidence=0.8,
            expected_outcome="Price up",
            realized_outcome="PENDING",
            pnl=0.0,
            lesson="",
        )

        similar = self.memory.find_similar(current, top_k=5)
        self.assertEqual(len(similar), 1)
        self.assertIsInstance(similar[0], SimilarExperience)
        self.assertGreater(similar[0].similarity_score, 0.5)

    def test_performance_summary(self):
        """Verify performance summary computation."""
        exp1 = TradeExperience(
            timestamp=datetime.now(),
            symbol="AAPL",
            regime="R01",
            regime_probabilities={"R01": 0.8},
            agent_signals={"agent1": 0.5},
            ensemble_signal=0.5,
            disagreement=0.2,
            effective_confidence=0.8,
            kalman_gain=0.5,
            kalman_price=100.0,
            kalman_trend=0.01,
            capital_gate_verdict="ALLOW",
            effective_cap=0.5,
            state_charges={"economic": 1.0},
            position_action="BUY",
            quantity=1.0,
            confidence=0.8,
            expected_outcome="Price up",
            realized_outcome="PENDING",
            pnl=100.0,
            lesson="",
        )
        exp2 = TradeExperience(
            timestamp=datetime.now(),
            symbol="AAPL",
            regime="R01",
            regime_probabilities={"R01": 0.8},
            agent_signals={"agent1": 0.5},
            ensemble_signal=0.5,
            disagreement=0.2,
            effective_confidence=0.8,
            kalman_gain=0.5,
            kalman_price=100.0,
            kalman_trend=0.01,
            capital_gate_verdict="ALLOW",
            effective_cap=0.5,
            state_charges={"economic": 1.0},
            position_action="BUY",
            quantity=1.0,
            confidence=0.8,
            expected_outcome="Price up",
            realized_outcome="PENDING",
            pnl=-50.0,
            lesson="",
        )
        self.memory.log_experience(exp1)
        self.memory.log_experience(exp2)

        summary = self.memory.get_performance_summary()
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["wins"], 1)
        self.assertEqual(summary["losses"], 1)
        self.assertEqual(summary["total_pnl"], 50.0)

    def test_memory_limits_enforced(self):
        """Verify per-symbol memory limits are enforced."""
        # Create many experiences for same symbol
        for i in range(MAX_MEMORY_PER_SYMBOL + 10):
            exp = TradeExperience(
                timestamp=datetime.now(),
                symbol="AAPL",
                regime="R01",
                regime_probabilities={"R01": 0.8},
                agent_signals={"agent1": 0.5},
                ensemble_signal=0.5,
                disagreement=0.2,
                effective_confidence=0.8,
                kalman_gain=0.5,
                kalman_price=100.0,
                kalman_trend=0.01,
                capital_gate_verdict="ALLOW",
                effective_cap=0.5,
                state_charges={"economic": 1.0},
                position_action="BUY",
                quantity=1.0,
                confidence=0.8,
                expected_outcome="Price up",
                realized_outcome="PENDING",
                pnl=0.0,
                lesson="",
            )
            self.memory.log_experience(exp)

        history = self.memory.get_history("AAPL")
        self.assertLessEqual(len(history), MAX_MEMORY_PER_SYMBOL)


# ---------------------------------------------------------------------------
# Test Orchestrator
# ---------------------------------------------------------------------------

class TestOrchestrator(unittest.TestCase):
    """Test X Quant X orchestrator."""

    def test_orchestrator_initialization(self):
        """Verify orchestrator initializes correctly."""
        orchestrator = XQuantXOrchestrator(
            agent_ids=AGENT_IDS,
            symbol="AAPL",
            use_hmm=False,
            enable_trading=False,
        )
        self.assertIsNotNone(orchestrator)

    def test_orchestrator_rejects_empty_agent_ids(self):
        """Verify orchestrator rejects empty agent_ids."""
        with self.assertRaises(ValueError):
            XQuantXOrchestrator(
                agent_ids=[],
                symbol="AAPL",
            )

    def test_orchestrator_rejects_empty_symbol(self):
        """Verify orchestrator rejects empty symbol."""
        with self.assertRaises(ValueError):
            XQuantXOrchestrator(
                agent_ids=AGENT_IDS,
                symbol="",
            )

    def test_run_cycle_returns_result(self):
        """Verify run_cycle returns CycleResult."""
        orchestrator = XQuantXOrchestrator(
            agent_ids=AGENT_IDS,
            symbol="AAPL",
            use_hmm=False,
            enable_trading=False,
        )

        prices = [100.0 + i * 0.1 for i in range(45)]
        volumes = [1000.0] * 45
        agents = make_agent_outputs(
            signals=[0.5] * 7,
            confidences=[0.9] * 7,
        )

        from investment_agent.capital.capital_gate import SevenStateVector
        states = SevenStateVector(
            economic=1.0, financial=1.0, fiscal=1.0,
            portfolio=1.0, fundamental=1.0, market=1.0, sector=1.0
        )

        result = orchestrator.run_cycle(
            prices=prices,
            volumes=volumes,
            agent_outputs=agents,
            states=states,
            portfolio_context={
                "position_pct": 0.05,
                "gross_leverage": 0.5,
                "entropy": 0.1,
                "drawdown_pct": 0.01,
                "execution_timeout_seconds": 5.0,
                "sector_exposure_pct": 0.1,
                "is_new_long": False,
                "regime": "R01",
            },
        )

        self.assertIsInstance(result, CycleResult)
        self.assertIsInstance(result.decision, TradingDecision)
        self.assertIn(result.regime.regime, VALID_REGIMES)
        self.assertEqual(len(result.weights), 7)

    def test_run_cycle_records_experience(self):
        """Verify run_cycle records trade experience."""
        orchestrator = XQuantXOrchestrator(
            agent_ids=AGENT_IDS,
            symbol="AAPL",
            use_hmm=False,
            enable_trading=False,
        )

        prices = [100.0 + i * 0.1 for i in range(45)]
        volumes = [1000.0] * 45
        agents = make_agent_outputs(
            signals=[0.5] * 7,
            confidences=[0.9] * 7,
        )

        from investment_agent.capital.capital_gate import SevenStateVector
        states = SevenStateVector(
            economic=1.0, financial=1.0, fiscal=1.0,
            portfolio=1.0, fundamental=1.0, market=1.0, sector=1.0
        )

        result = orchestrator.run_cycle(
            prices=prices,
            volumes=volumes,
            agent_outputs=agents,
            states=states,
            portfolio_context={
                "position_pct": 0.05,
                "gross_leverage": 0.5,
                "entropy": 0.1,
                "drawdown_pct": 0.01,
                "execution_timeout_seconds": 5.0,
                "sector_exposure_pct": 0.1,
                "is_new_long": False,
                "regime": "R01",
            },
        )

        self.assertIsInstance(result.experience, TradeExperience)
        self.assertEqual(result.experience.symbol, "AAPL")
        self.assertEqual(result.experience.position_action, result.decision.action)

    def test_run_cycle_provenance_trace(self):
        """Verify run_cycle produces complete provenance."""
        orchestrator = XQuantXOrchestrator(
            agent_ids=AGENT_IDS,
            symbol="AAPL",
            use_hmm=False,
            enable_trading=False,
        )

        prices = [100.0 + i * 0.1 for i in range(45)]
        volumes = [1000.0] * 45
        agents = make_agent_outputs(
            signals=[0.5] * 7,
            confidences=[0.9] * 7,
        )

        from investment_agent.capital.capital_gate import SevenStateVector
        states = SevenStateVector(
            economic=1.0, financial=1.0, fiscal=1.0,
            portfolio=1.0, fundamental=1.0, market=1.0, sector=1.0
        )

        result = orchestrator.run_cycle(
            prices=prices,
            volumes=volumes,
            agent_outputs=agents,
            states=states,
            portfolio_context={
                "position_pct": 0.05,
                "gross_leverage": 0.5,
                "entropy": 0.1,
                "drawdown_pct": 0.01,
                "execution_timeout_seconds": 5.0,
                "sector_exposure_pct": 0.1,
                "is_new_long": False,
                "regime": "R01",
            },
        )

        # Verify provenance completeness
        provenance = result.decision.provenance
        self.assertIn("regime", provenance)
        self.assertIn("ensemble_signal", provenance)
        self.assertIn("kalman_gain", provenance)
        self.assertIn("effective_cap", provenance)
        self.assertIn("verdict", provenance)
        self.assertIn("weights", provenance)


if __name__ == "__main__":
    unittest.main()
