"""Unit tests for hedge_signal.py -- drop detection and the hedge_capital_bridge wiring."""

import unittest
from unittest.mock import patch, MagicMock

from investment_agent.signals import hedge_signal
from investment_agent.execution.hedge_capital_bridge import _hedge_state


class TestCheckForDrop(unittest.TestCase):
    def test_not_enough_data_returns_false(self):
        with patch.object(hedge_signal, "get_recent_prices", return_value=[100.0]):
            dropped, pct = hedge_signal.check_for_drop("AAPL")
            self.assertFalse(dropped)
            self.assertEqual(pct, 0.0)

    def test_detects_drop_above_threshold(self):
        with patch.object(hedge_signal, "get_recent_prices", return_value=[100.0, 105.0, 95.0]):
            # high=105, current=95 -> drop = 9.52%, threshold is 3%
            dropped, pct = hedge_signal.check_for_drop("AAPL")
            self.assertTrue(dropped)
            self.assertAlmostEqual(pct, (105.0 - 95.0) / 105.0, places=4)

    def test_no_drop_below_threshold(self):
        with patch.object(hedge_signal, "get_recent_prices", return_value=[100.0, 100.5, 100.2]):
            dropped, pct = hedge_signal.check_for_drop("AAPL")
            self.assertFalse(dropped)

    def test_boundary_exact_threshold_counts_as_dropped(self):
        # high=100, current=97 -> exactly 3% drop, threshold is >=
        with patch.object(hedge_signal, "get_recent_prices", return_value=[100.0, 97.0]):
            dropped, pct = hedge_signal.check_for_drop("AAPL")
            self.assertTrue(dropped)


class TestRunHedgeCheck(unittest.TestCase):
    def setUp(self):
        _hedge_state._recent_hedges.clear()

    def test_blocked_verdict_skips_order(self):
        blocked_assessment = MagicMock(verdict="BLOCK", reasons=("no drop",))
        with patch.object(hedge_signal, "evaluate_hedge_risk", return_value=blocked_assessment):
            with patch.object(hedge_signal, "place_order") as mock_place:
                hedge_signal.run_hedge_check("AAPL")
                mock_place.assert_not_called()

    def test_skips_when_already_hedged_recently_in_memory(self):
        allow_assessment = MagicMock(verdict="ALLOW", adjusted_quantity=1, drop_pct=0.05, reasons=("drop",))
        with patch.object(hedge_signal, "evaluate_hedge_risk", return_value=allow_assessment):
            with patch.object(hedge_signal, "already_hedged_recently", return_value=True):
                with patch.object(hedge_signal, "place_order") as mock_place:
                    hedge_signal.run_hedge_check("AAPL")
                    mock_place.assert_not_called()

    def test_places_order_with_bridge_adjusted_quantity(self):
        allow_assessment = MagicMock(verdict="ALLOW", adjusted_quantity=3, drop_pct=0.09, reasons=("drop",))
        fake_contract = MagicMock(symbol="AAPL250101P00100000", close_price=2.5)
        fake_order_result = MagicMock(id="order-99")

        with patch.object(hedge_signal, "evaluate_hedge_risk", return_value=allow_assessment):
            with patch.object(hedge_signal, "already_hedged_recently", return_value=False):
                with patch.object(hedge_signal, "get_option_contract", return_value=fake_contract):
                    with patch.object(hedge_signal, "place_order", return_value=fake_order_result) as mock_place:
                        with patch.object(hedge_signal, "log_decision") as mock_log:
                            with patch.object(hedge_signal, "record_hedge_placement") as mock_record:
                                hedge_signal.run_hedge_check("AAPL")

                                mock_place.assert_called_once_with(
                                    "AAPL250101P00100000", "buy", qty=3, price_per_contract=2.5
                                )
                                mock_log.assert_called_once()
                                mock_record.assert_called_once_with("AAPL")

    def test_does_not_log_when_order_blocked_by_safety_check(self):
        allow_assessment = MagicMock(verdict="ALLOW", adjusted_quantity=1, drop_pct=0.05, reasons=("drop",))
        fake_contract = MagicMock(symbol="AAPL250101P00100000", close_price=2.5)

        with patch.object(hedge_signal, "evaluate_hedge_risk", return_value=allow_assessment):
            with patch.object(hedge_signal, "already_hedged_recently", return_value=False):
                with patch.object(hedge_signal, "get_option_contract", return_value=fake_contract):
                    with patch.object(hedge_signal, "place_order", return_value=None):
                        with patch.object(hedge_signal, "log_decision") as mock_log:
                            with patch.object(hedge_signal, "record_hedge_placement") as mock_record:
                                hedge_signal.run_hedge_check("AAPL")
                                mock_log.assert_not_called()
                                mock_record.assert_not_called()

    def test_reduce_verdict_still_places_order(self):
        reduce_assessment = MagicMock(verdict="REDUCE", adjusted_quantity=1, drop_pct=0.05, reasons=("reduced",))
        fake_contract = MagicMock(symbol="AAPL250101P00100000", close_price=2.5)
        fake_order_result = MagicMock(id="order-1")

        with patch.object(hedge_signal, "evaluate_hedge_risk", return_value=reduce_assessment):
            with patch.object(hedge_signal, "already_hedged_recently", return_value=False):
                with patch.object(hedge_signal, "get_option_contract", return_value=fake_contract):
                    with patch.object(hedge_signal, "place_order", return_value=fake_order_result) as mock_place:
                        hedge_signal.run_hedge_check("AAPL")
                        mock_place.assert_called_once()


if __name__ == "__main__":
    unittest.main()