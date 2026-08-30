"""Unit tests for memory.py -- decision logging and reflection."""

import json
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import memory


class MemoryTestCase(unittest.TestCase):
    def setUp(self):
        self._original_memory_file = memory.MEMORY_FILE
        memory.MEMORY_FILE = "test_memory_log.json"
        if os.path.exists(memory.MEMORY_FILE):
            os.remove(memory.MEMORY_FILE)

    def tearDown(self):
        if os.path.exists(memory.MEMORY_FILE):
            os.remove(memory.MEMORY_FILE)
        memory.MEMORY_FILE = self._original_memory_file


class TestLogDecision(MemoryTestCase):
    def test_creates_file_and_appends_record(self):
        memory.log_decision("AAPL", 0.05, "buy", "order-1", 150.0)
        with open(memory.MEMORY_FILE) as f:
            records = json.load(f)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["symbol"], "AAPL")
        self.assertEqual(records[0]["action"], "buy")
        self.assertEqual(records[0]["order_id"], "order-1")

    def test_appends_multiple_records(self):
        memory.log_decision("AAPL", 0.05, "buy", "order-1", 150.0)
        memory.log_decision("TSLA", 0.08, "buy", "order-2", 245.0)
        with open(memory.MEMORY_FILE) as f:
            records = json.load(f)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["symbol"], "TSLA")


class TestAlreadyHedgedRecently(MemoryTestCase):
    def test_false_when_no_records(self):
        self.assertFalse(memory.already_hedged_recently("AAPL"))

    def test_true_within_window(self):
        memory.log_decision("AAPL", 0.05, "buy", "order-1", 150.0)
        self.assertTrue(memory.already_hedged_recently("AAPL", days=3))

    def test_false_outside_window(self):
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
        with open(memory.MEMORY_FILE, "w") as f:
            json.dump([{
                "symbol": "AAPL", "drop_pct": 0.05, "action": "buy",
                "order_id": "order-1", "price_at_decision": 150.0,
                "timestamp": old_timestamp,
            }], f)
        self.assertFalse(memory.already_hedged_recently("AAPL", days=3))

    def test_false_for_different_symbol(self):
        memory.log_decision("AAPL", 0.05, "buy", "order-1", 150.0)
        self.assertFalse(memory.already_hedged_recently("TSLA"))

    def test_ignores_non_buy_actions(self):
        memory.log_decision("AAPL", 0.05, "hold", None, 150.0)
        self.assertFalse(memory.already_hedged_recently("AAPL"))


class TestReflect(MemoryTestCase):
    def test_empty_for_unknown_symbol(self):
        result = memory.reflect("AAPL")
        self.assertEqual(result, [])

    def test_computes_helped_verdict_on_price_recovery(self):
        memory.log_decision("AAPL", 0.05, "buy", "order-1", 100.0)
        with patch.object(memory, "_get_latest_price", return_value=120.0):
            results = memory.reflect("AAPL")
        self.assertEqual(len(results), 1)
        self.assertIn("helped", results[0]["verdict"])
        self.assertEqual(results[0]["current_price"], 120.0)

    def test_computes_didnt_help_verdict_on_continued_drop(self):
        memory.log_decision("AAPL", 0.05, "buy", "order-1", 100.0)
        with patch.object(memory, "_get_latest_price", return_value=80.0):
            results = memory.reflect("AAPL")
        self.assertIn("didn't help", results[0]["verdict"])


if __name__ == "__main__":
    unittest.main()