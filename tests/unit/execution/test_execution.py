"""Unit tests for execution.py -- order placement and safety checks."""

import unittest
from unittest.mock import patch, MagicMock

from investment_agent.execution import execution


class TestIsTradeSafe(unittest.TestCase):
    def test_blocks_invalid_price(self):
        self.assertFalse(execution.is_trade_safe("AAPL", qty=1, price_per_contract=0))
        self.assertFalse(execution.is_trade_safe("AAPL", qty=1, price_per_contract=None))
        self.assertFalse(execution.is_trade_safe("AAPL", qty=1, price_per_contract=-5))

    def test_blocks_when_trade_cost_exceeds_limit(self):
        fake_client = MagicMock()
        fake_account = MagicMock(buying_power="1000.00")
        fake_client.get_account.return_value = fake_account
        with patch.object(execution, "_get_trading_client", return_value=fake_client):
            # trade_cost = 1 * 100 * 100 = 10000, max_allowed = 1000 * 0.05 = 50
            self.assertFalse(execution.is_trade_safe("AAPL", qty=1, price_per_contract=100.0))

    def test_allows_when_trade_cost_within_limit(self):
        fake_client = MagicMock()
        fake_account = MagicMock(buying_power="100000.00")
        fake_client.get_account.return_value = fake_account
        with patch.object(execution, "_get_trading_client", return_value=fake_client):
            # trade_cost = 1 * 1.0 * 100 = 100, max_allowed = 100000 * 0.05 = 5000
            self.assertTrue(execution.is_trade_safe("AAPL", qty=1, price_per_contract=1.0))

    def test_boundary_exact_limit_is_safe(self):
        fake_client = MagicMock()
        fake_account = MagicMock(buying_power="10000.00")
        fake_client.get_account.return_value = fake_account
        with patch.object(execution, "_get_trading_client", return_value=fake_client):
            # max_allowed = 10000 * 0.05 = 500; trade_cost = 1 * 5.0 * 100 = 500 -> not > max_allowed
            self.assertTrue(execution.is_trade_safe("AAPL", qty=1, price_per_contract=5.0))


class TestPlaceOrder(unittest.TestCase):
    def test_returns_none_when_unsafe(self):
        with patch.object(execution, "is_trade_safe", return_value=False):
            result = execution.place_order("AAPL", "buy", qty=1, price_per_contract=100.0)
            self.assertIsNone(result)

    def test_submits_order_when_safe(self):
        fake_client = MagicMock()
        fake_result = MagicMock(status="filled", id="order-1")
        fake_client.submit_order.return_value = fake_result
        with patch.object(execution, "is_trade_safe", return_value=True):
            with patch.object(execution, "_get_trading_client", return_value=fake_client):
                result = execution.place_order("AAPL", "buy", qty=2, price_per_contract=1.0)
                self.assertEqual(result, fake_result)
                fake_client.submit_order.assert_called_once()
                sent_order = fake_client.submit_order.call_args[0][0]
                self.assertEqual(sent_order.qty, 2)
                self.assertEqual(sent_order.symbol, "AAPL")

    def test_sell_side_maps_correctly(self):
        fake_client = MagicMock()
        fake_result = MagicMock(status="filled", id="order-2")
        fake_client.submit_order.return_value = fake_result
        with patch.object(execution, "is_trade_safe", return_value=True):
            with patch.object(execution, "_get_trading_client", return_value=fake_client):
                execution.place_order("AAPL", "sell", qty=1, price_per_contract=1.0)
                sent_order = fake_client.submit_order.call_args[0][0]
                self.assertEqual(sent_order.side, execution.OrderSide.SELL)


class TestGetOptionContract(unittest.TestCase):
    def test_raises_when_no_contracts_found(self):
        fake_client = MagicMock()
        fake_response = MagicMock(option_contracts=[])
        fake_client.get_option_contracts.return_value = fake_response
        with patch.object(execution, "_get_trading_client", return_value=fake_client):
            with self.assertRaises(ValueError):
                execution.get_option_contract("AAPL", option_type="put")

    def test_returns_first_contract(self):
        fake_client = MagicMock()
        fake_contract = MagicMock(symbol="AAPL250101P00100000", close_price=2.5)
        fake_response = MagicMock(option_contracts=[fake_contract])
        fake_client.get_option_contracts.return_value = fake_response
        with patch.object(execution, "_get_trading_client", return_value=fake_client):
            result = execution.get_option_contract("AAPL", option_type="put")
            self.assertEqual(result, fake_contract)


if __name__ == "__main__":
    unittest.main()