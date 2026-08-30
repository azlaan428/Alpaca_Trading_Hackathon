"""Tests for market feature extractor."""

import unittest
from typing import List

import numpy as np

from investment_agent.regimes.market_feature_extractor import (
    extract_features,
    extract_single_feature_vector,
    MarketFeatures,
)


class TestMarketFeatureExtractor(unittest.TestCase):
    """Test market feature extraction."""

    def test_extract_features_returns_correct_shape(self):
        """Verify feature extraction returns T x 7 matrix."""
        prices = [100.0 + i * 0.1 for i in range(50)]
        features = extract_features(prices, lookback_days=20)
        self.assertEqual(features.shape[1], 7)

    def test_extract_features_with_volumes(self):
        """Verify feature extraction works with volumes."""
        prices = [100.0 + i * 0.1 for i in range(50)]
        volumes = [1000.0 + i * 10 for i in range(50)]
        features = extract_features(prices, volumes, lookback_days=20)
        self.assertEqual(features.shape[1], 7)

    def test_extract_features_insufficient_prices_raises(self):
        """Verify ValueError for insufficient price data."""
        prices = [100.0, 101.0, 102.0]
        with self.assertRaises(ValueError):
            extract_features(prices)

    def test_extract_features_rejects_nan_prices(self):
        """Verify NaN prices are rejected."""
        prices = [100.0] * 35
        prices[10] = float("nan")
        with self.assertRaises(ValueError):
            extract_features(prices)

    def test_extract_features_rejects_inf_prices(self):
        """Verify Infinity prices are rejected."""
        prices = [100.0] * 35
        prices[10] = float("inf")
        with self.assertRaises(ValueError):
            extract_features(prices)

    def test_extract_features_rejects_zero_prices(self):
        """Verify zero prices are rejected."""
        prices = [100.0] * 35
        prices[10] = 0.0
        with self.assertRaises(ValueError):
            extract_features(prices)

    def test_extract_single_feature_vector(self):
        """Verify single feature vector extraction."""
        prices = [100.0 + i * 0.1 for i in range(50)]
        volumes = [1000.0 + i * 10 for i in range(50)]
        vector = extract_single_feature_vector(prices, volumes)
        self.assertEqual(vector.shape, (1, 7))

    def test_rsi_in_valid_range(self):
        """Verify RSI is in valid range [0, 100]."""
        prices = [100.0 + i * 0.1 for i in range(50)]
        features = extract_features(prices, lookback_days=20)
        rsi_values = features[:, 0]
        self.assertTrue(np.all(rsi_values >= 0))
        self.assertTrue(np.all(rsi_values <= 100))

    def test_vol_ratio_positive(self):
        """Verify volume ratio is positive."""
        prices = [100.0 + i * 0.1 for i in range(50)]
        volumes = [1000.0 + i * 10 for i in range(50)]
        features = extract_features(prices, volumes, lookback_days=20)
        vol_ratios = features[:, 4]
        self.assertTrue(np.all(vol_ratios > 0))


if __name__ == "__main__":
    unittest.main()
