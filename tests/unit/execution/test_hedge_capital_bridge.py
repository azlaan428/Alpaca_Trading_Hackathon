"""Adversarial unit test suite for hedge_capital_bridge.py.

Verifies risk-adjusted hedge sizing, recent hedge detection, verdict logic,
and state tracker behavior.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from investment_agent.execution.hedge_capital_bridge import (
    HedgeRiskAssessment,
    evaluate_hedge_risk,
    record_hedge_placement,
    cleanup_hedge_history,
    get_recent_hedge_symbols,
    _hedge_state,
)


class TestHedgeRiskAssessment(unittest.TestCase):
    """Test HedgeRiskAssessment dataclass."""

    def test_assessment_creation(self):
        """Verify HedgeRiskAssessment can be created with valid fields."""
        assessment = HedgeRiskAssessment(
            symbol="AAPL",
            drop_pct=0.05,
            base_quantity=1,
            risk_multiplier=0.8,
            adjusted_quantity=1,
            already_hedged_recently=False,
            account_capacity_ratio=0.3,
            verdict="ALLOW",
            reasons=("Drop detected: 5.00%", "Final quantity: 1 contracts"),
        )
        self.assertEqual(assessment.symbol, "AAPL")
        self.assertEqual(assessment.verdict, "ALLOW")
        self.assertEqual(len(assessment.reasons), 2)

    def test_assessment_is_frozen(self):
        """Verify HedgeRiskAssessment is immutable."""
        assessment = HedgeRiskAssessment(
            symbol="AAPL",
            drop_pct=0.05,
            base_quantity=1,
            risk_multiplier=0.8,
            adjusted_quantity=1,
            already_hedged_recently=False,
            account_capacity_ratio=0.3,
            verdict="ALLOW",
            reasons=(),
        )
        with self.assertRaises(AttributeError):
            assessment.verdict = "BLOCK"


class TestEvaluateHedgeRisk(unittest.TestCase):
    """Test evaluate_hedge_risk() function."""

    def setUp(self):
        """Reset hedge state tracker before each test."""
        _hedge_state._recent_hedges.clear()

    def test_no_drop_returns_block(self):
        """Verify BLOCK verdict when no significant drop is detected."""
        with patch("investment_agent.execution.hedge_capital_bridge._get_check_for_drop") as mock_get:
            mock_get.return_value = (lambda s: (False, 0.01), 0.03)
            result = evaluate_hedge_risk("AAPL")
            self.assertEqual(result.verdict, "BLOCK")
            self.assertEqual(result.adjusted_quantity, 0)
            self.assertEqual(result.risk_multiplier, 0.0)

    def test_drop_detected_returns_allow(self):
        """Verify ALLOW verdict when drop is detected and no recent hedge."""
        with patch("investment_agent.execution.hedge_capital_bridge._get_check_for_drop") as mock_get:
            mock_get.return_value = (lambda s: (True, 0.05), 0.03)
            with patch("investment_agent.execution.hedge_capital_bridge._get_execution_utils") as mock_exec:
                mock_exec.return_value = (lambda *a, **k: True, 0.05, lambda *a, **k: MagicMock(close_price=5.0))
                with patch.dict("os.environ", {"MAX_BUYING_POWER": "100000"}):
                    result = evaluate_hedge_risk("AAPL", base_quantity=1)
                    self.assertEqual(result.verdict, "ALLOW")
                    self.assertGreater(result.adjusted_quantity, 0)
                    self.assertGreater(result.risk_multiplier, 0.0)

    def test_recent_hedge_reduces_multiplier(self):
        """Verify multiplier is reduced when recently hedged."""
        with patch("investment_agent.execution.hedge_capital_bridge._get_check_for_drop") as mock_get:
            mock_get.return_value = (lambda s: (True, 0.05), 0.03)
            with patch("investment_agent.execution.hedge_capital_bridge._get_execution_utils") as mock_exec:
                mock_exec.return_value = (lambda *a, **k: True, 0.05, lambda *a, **k: MagicMock(close_price=5.0))
                with patch.dict("os.environ", {"MAX_BUYING_POWER": "100000"}):
                    record_hedge_placement("AAPL")
                    result = evaluate_hedge_risk("AAPL", base_quantity=1)
                    self.assertTrue(result.already_hedged_recently)
                    self.assertLess(result.risk_multiplier, 1.0)
                    self.assertEqual(result.verdict, "REDUCE")

    def test_large_drop_increases_multiplier(self):
        """Verify larger drops produce larger risk multipliers."""
        with patch("investment_agent.execution.hedge_capital_bridge._get_check_for_drop") as mock_get:
            mock_get.return_value = (lambda s: (True, 0.15), 0.03)
            with patch("investment_agent.execution.hedge_capital_bridge._get_execution_utils") as mock_exec:
                mock_exec.return_value = (lambda *a, **k: True, 0.05, lambda *a, **k: MagicMock(close_price=5.0))
                with patch.dict("os.environ", {"MAX_BUYING_POWER": "100000"}):
                    result = evaluate_hedge_risk("AAPL", base_quantity=2)
                    self.assertEqual(result.verdict, "ALLOW")
                    self.assertEqual(result.adjusted_quantity, 2)
                    self.assertAlmostEqual(result.risk_multiplier, 1.0, places=5)

    def test_account_capacity_blocks_large_trades(self):
        """Verify BLOCK verdict when trade cost exceeds account capacity."""
        with patch("investment_agent.execution.hedge_capital_bridge._get_check_for_drop") as mock_get:
            mock_get.return_value = (lambda s: (True, 0.05), 0.03)
            with patch("investment_agent.execution.hedge_capital_bridge._get_execution_utils") as mock_exec:
                mock_exec.return_value = (lambda *a, **k: True, 0.05, lambda *a, **k: MagicMock(close_price=1000.0))
                with patch.dict("os.environ", {"MAX_BUYING_POWER": "10000"}):
                    result = evaluate_hedge_risk("AAPL", base_quantity=1)
                    self.assertEqual(result.verdict, "BLOCK")
                    self.assertEqual(result.adjusted_quantity, 0)

    def test_invalid_symbol_raises_type_error(self):
        """Verify TypeError for invalid symbol."""
        with self.assertRaises(TypeError):
            evaluate_hedge_risk(123)

    def test_invalid_quantity_raises_value_error(self):
        """Verify ValueError for non-positive base_quantity."""
        with patch("investment_agent.execution.hedge_capital_bridge._get_check_for_drop") as mock_get:
            mock_get.return_value = (lambda s: (True, 0.05), 0.03)
            with self.assertRaises(ValueError):
                evaluate_hedge_risk("AAPL", base_quantity=0)
            with self.assertRaises(ValueError):
                evaluate_hedge_risk("AAPL", base_quantity=-1)

    def test_invalid_lookback_raises_value_error(self):
        """Verify ValueError for negative lookback_days."""
        with self.assertRaises(ValueError):
            evaluate_hedge_risk("AAPL", lookback_days=-1)

    def test_invalid_multipliers_raise_value_error(self):
        """Verify ValueError for invalid multiplier ranges."""
        with self.assertRaises(ValueError):
            evaluate_hedge_risk("AAPL", min_multiplier=-0.1)
        with self.assertRaises(ValueError):
            evaluate_hedge_risk("AAPL", max_multiplier=0.0)
        with self.assertRaises(ValueError):
            evaluate_hedge_risk("AAPL", min_multiplier=0.5, max_multiplier=0.3)


class TestHedgeStateTracker(unittest.TestCase):
    """Test _HedgeStateTracker functionality."""

    def setUp(self):
        """Reset hedge state tracker before each test."""
        _hedge_state._recent_hedges.clear()

    def test_record_and_check_hedge(self):
        """Verify hedge recording and recent detection."""
        record_hedge_placement("AAPL")
        self.assertTrue(_hedge_state.was_hedged_recently("AAPL", lookback_days=1))

    def test_old_hedge_not_recent(self):
        """Verify hedges older than lookback are not considered recent."""
        _hedge_state._recent_hedges["AAPL"] = [datetime.now() - timedelta(days=10)]
        self.assertFalse(_hedge_state.was_hedged_recently("AAPL", lookback_days=3))

    def test_multiple_symbols_tracked(self):
        """Verify multiple symbols can be tracked independently."""
        record_hedge_placement("AAPL")
        record_hedge_placement("GOOGL")
        self.assertTrue(_hedge_state.was_hedged_recently("AAPL"))
        self.assertTrue(_hedge_state.was_hedged_recently("GOOGL"))
        self.assertFalse(_hedge_state.was_hedged_recently("MSFT"))

    def test_cleanup_removes_old_entries(self):
        """Verify cleanup removes old hedge records."""
        _hedge_state._recent_hedges["AAPL"] = [datetime.now() - timedelta(days=10)]
        _hedge_state._recent_hedges["GOOGL"] = [datetime.now()]
        cleanup_hedge_history(max_age_days=5)
        self.assertNotIn("AAPL", _hedge_state._recent_hedges)
        self.assertIn("GOOGL", _hedge_state._recent_hedges)

    def test_get_recent_hedge_symbols(self):
        """Verify get_recent_hedge_symbols returns correct list."""
        _hedge_state._recent_hedges["AAPL"] = [datetime.now()]
        _hedge_state._recent_hedges["GOOGL"] = [datetime.now() - timedelta(days=10)]
        recent = get_recent_hedge_symbols(lookback_days=3)
        self.assertIn("AAPL", recent)
        self.assertNotIn("GOOGL", recent)


if __name__ == "__main__":
    unittest.main()
