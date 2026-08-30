"""Adversarial unit test suite for regime_detector.py.

Verifies market regime classification, feature extraction, confidence calculation,
regime affinity scores, and history tracking.
"""

import math
import unittest
from datetime import datetime, timedelta
from typing import List

from investment_agent.regimes.regime_detector import (
    RegimeClassification,
    RegimeDetector,
    MarketFeatures,
    detect_regime,
    _extract_features,
    _compute_confidence,
    _compute_regime_affinity,
    _compute_transition_probabilities,
    _validate_prices,
    _validate_volumes,
    _validate_lengths,
    _REGIME_MAP,
)


class TestMarketFeatures(unittest.TestCase):
    """Test MarketFeatures dataclass."""

    def test_features_creation(self):
        """Verify MarketFeatures can be created with valid fields."""
        features = MarketFeatures(
            returns=[0.01, -0.02, 0.03],
            annualized_return=0.05,
            annualized_volatility=0.20,
            volume_ratio=1.2,
            trend_strength=0.05,
            volatility_regime="normal",
            volume_regime="normal",
        )
        self.assertEqual(features.annualized_return, 0.05)
        self.assertEqual(features.volatility_regime, "normal")

    def test_features_is_frozen(self):
        """Verify MarketFeatures is immutable."""
        features = MarketFeatures(
            returns=[0.01],
            annualized_return=0.05,
            annualized_volatility=0.20,
            volume_ratio=1.2,
            trend_strength=0.05,
            volatility_regime="normal",
            volume_regime="normal",
        )
        with self.assertRaises(AttributeError):
            features.volatility_regime = "elevated"


class TestValidationHelpers(unittest.TestCase):
    """Test input validation functions."""

    def test_zero_price_raises_error(self):
        """Verify zero price raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_prices([0.0, 100.0, 101.0])
        self.assertIn("non-positive", str(ctx.exception))

    def test_negative_price_raises_error(self):
        """Verify negative price raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_prices([-1.0, 100.0])
        self.assertIn("non-positive", str(ctx.exception))

    def test_nan_price_raises_error(self):
        """Verify NaN price raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_prices([float("nan"), 100.0])
        self.assertIn("NaN", str(ctx.exception))

    def test_inf_price_raises_error(self):
        """Verify infinite price raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_prices([float("inf"), 100.0])
        self.assertIn("Infinity", str(ctx.exception))

    def test_negative_volume_raises_error(self):
        """Verify negative volume raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_volumes([-1.0, 1000.0])
        self.assertIn("negative", str(ctx.exception))

    def test_nan_volume_raises_error(self):
        """Verify NaN volume raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_volumes([float("nan"), 1000.0])
        self.assertIn("NaN", str(ctx.exception))

    def test_inf_volume_raises_error(self):
        """Verify infinite volume raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_volumes([float("inf"), 1000.0])
        self.assertIn("Infinity", str(ctx.exception))

    def test_volume_shorter_than_prices_raises_error(self):
        """Verify volume series shorter than prices raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _validate_lengths([100.0, 101.0], [1000.0])
        self.assertIn("shorter", str(ctx.exception))

    def test_volume_longer_than_prices_accepted(self):
        """Verify volume series longer than prices is accepted."""
        _validate_lengths([100.0, 101.0], [1000.0, 2000.0, 3000.0])

    def test_exactly_40_volume_observations_accepted(self):
        """Verify exactly 40 volume observations are accepted for 20-day lookback."""
        prices = [100.0] * 45
        volumes = [1000.0] * 40 + [2000.0] * 5
        _validate_lengths(prices, volumes)

    def test_39_volume_observations_marked_unavailable(self):
        """Verify 39 volume observations are marked as unavailable for 20-day lookback."""
        prices = [100.0] * 39
        volumes = [1000.0] * 39
        features = _extract_features(prices, volumes, lookback_days=20)
        self.assertEqual(features.volume_regime, "unavailable")
        self.assertTrue(math.isnan(features.volume_ratio))


class TestFeatureExtraction(unittest.TestCase):
    """Test _extract_features() function."""

    def test_steady_uptrend_produces_positive_return(self):
        """Verify steady uptrend produces positive annualized return."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        features = _extract_features(prices, lookback_days=20)
        self.assertGreater(features.annualized_return, 0.0)

    def test_steady_downtrend_produces_negative_return(self):
        """Verify steady downtrend produces negative annualized return."""
        prices = [100.0 - i * 0.5 for i in range(25)]
        features = _extract_features(prices, lookback_days=20)
        self.assertLess(features.annualized_return, 0.0)

    def test_high_volatility_detected(self):
        """Verify high volatility is detected from alternating returns."""
        prices = [100.0]
        for i in range(24):
            if i % 2 == 0:
                prices.append(prices[-1] * 0.95)
            else:
                prices.append(prices[-1] * 1.05)
        features = _extract_features(prices, lookback_days=20)
        self.assertGreater(features.annualized_volatility, 0.2)

    def test_volume_ratio_calculation(self):
        """Verify volume ratio is computed correctly."""
        prices = [100.0] * 25
        volumes = [1000.0] * 30 + [2000.0] * 10
        features = _extract_features(prices, volumes, lookback_days=10)
        self.assertEqual(features.volume_regime, "elevated")
        self.assertGreater(features.volume_ratio, 1.5)

    def test_insufficient_prices_raises_error(self):
        """Verify ValueError for insufficient price data."""
        with self.assertRaises(ValueError):
            _extract_features([100.0])

    def test_zero_price_raises_error(self):
        """Verify zero price raises ValueError."""
        with self.assertRaises(ValueError):
            _extract_features([0.0, 100.0, 101.0])


class TestRegimeMapping(unittest.TestCase):
    """Test regime mapping logic."""

    def test_bullish_normal_normal_maps_to_R01(self):
        """Verify bullish + normal vol + normal volume maps to R01."""
        regime = _REGIME_MAP.get(("bullish", "normal", "normal"))
        self.assertEqual(regime, "R01")

    def test_bearish_elevated_elevated_maps_to_R12(self):
        """Verify bearish + elevated vol + elevated volume maps to R12."""
        regime = _REGIME_MAP.get(("bearish", "elevated", "elevated"))
        self.assertEqual(regime, "R12")

    def test_all_12_combinations_mapped(self):
        """Verify all 12 regime combinations have valid mappings."""
        self.assertEqual(len(_REGIME_MAP), 12)
        for key, regime in _REGIME_MAP.items():
            self.assertIn(regime, [f"R{i:02d}" for i in range(1, 13)])


class TestConfidenceComputation(unittest.TestCase):
    """Test _compute_confidence() function."""

    def test_strong_trend_high_confidence(self):
        """Verify high confidence for strong trend."""
        features = MarketFeatures(
            returns=[0.02],
            annualized_return=0.50,
            annualized_volatility=0.10,
            volume_ratio=1.0,
            trend_strength=0.50,
            volatility_regime="normal",
            volume_regime="normal",
        )
        confidence = _compute_confidence(features)
        self.assertGreater(confidence, 0.5)

    def test_neutral_trend_lower_confidence(self):
        """Verify lower confidence for neutral trend."""
        features = MarketFeatures(
            returns=[0.001],
            annualized_return=0.001,
            annualized_volatility=0.10,
            volume_ratio=1.0,
            trend_strength=0.001,
            volatility_regime="normal",
            volume_regime="normal",
        )
        confidence = _compute_confidence(features)
        self.assertLess(confidence, 0.5)

    def test_confidence_bounded(self):
        """Verify confidence is bounded in [0.0, 1.0]."""
        features = MarketFeatures(
            returns=[0.02],
            annualized_return=0.50,
            annualized_volatility=0.50,
            volume_ratio=3.0,
            trend_strength=0.50,
            volatility_regime="elevated",
            volume_regime="elevated",
        )
        confidence = _compute_confidence(features)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)


class TestRegimeAffinity(unittest.TestCase):
    """Test _compute_regime_affinity() function."""

    def test_affinity_scores_sum_to_one(self):
        """Verify regime affinity scores sum to 1.0."""
        features = MarketFeatures(
            returns=[0.02],
            annualized_return=0.10,
            annualized_volatility=0.15,
            volume_ratio=1.0,
            trend_strength=0.10,
            volatility_regime="normal",
            volume_regime="normal",
        )
        probs = _compute_regime_affinity("R01", 0.8, features)
        self.assertAlmostEqual(sum(probs.values()), 1.0, places=5)

    def test_current_regime_has_highest_affinity(self):
        """Verify current regime receives highest affinity score."""
        features = MarketFeatures(
            returns=[0.02],
            annualized_return=0.10,
            annualized_volatility=0.15,
            volume_ratio=1.0,
            trend_strength=0.10,
            volatility_regime="normal",
            volume_regime="normal",
        )
        probs = _compute_regime_affinity("R01", 0.9, features)
        self.assertEqual(probs["R01"], max(probs.values()))

    def test_uniform_fallback_for_invalid_regime(self):
        """Verify uniform distribution fallback for invalid regime."""
        features = MarketFeatures(
            returns=[0.02],
            annualized_return=0.10,
            annualized_volatility=0.15,
            volume_ratio=1.0,
            trend_strength=0.10,
            volatility_regime="normal",
            volume_regime="normal",
        )
        probs = _compute_regime_affinity("INVALID", 0.5, features)
        uniform = 1.0 / len(probs)
        for prob in probs.values():
            self.assertAlmostEqual(prob, uniform, places=5)

    def test_backward_compat_transition_probs_alias(self):
        """Verify _compute_transition_probabilities is a backward-compatible alias."""
        features = MarketFeatures(
            returns=[0.02],
            annualized_return=0.10,
            annualized_volatility=0.15,
            volume_ratio=1.0,
            trend_strength=0.10,
            volatility_regime="normal",
            volume_regime="normal",
        )
        probs = _compute_transition_probabilities("R01", 0.8, features)
        self.assertAlmostEqual(sum(probs.values()), 1.0, places=5)


class TestRegimeDetector(unittest.TestCase):
    """Test RegimeDetector class."""

    def setUp(self):
        """Create fresh detector for each test."""
        self.detector = RegimeDetector(lookback_days=20)

    def test_steady_uptrend_classified_as_bullish(self):
        """Verify steady uptrend is classified as bullish regime."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        result = self.detector.classify(prices)
        self.assertEqual(result.regime, "R01")

    def test_steady_downtrend_classified_as_bearish(self):
        """Verify steady downtrend is classified as bearish regime."""
        prices = [100.0 - i * 0.5 for i in range(25)]
        result = self.detector.classify(prices)
        self.assertEqual(result.regime, "R09")

    def test_high_volatility_produces_elevated_regime(self):
        """Verify high volatility produces elevated volatility regime."""
        prices = [100.0]
        for i in range(24):
            if i % 2 == 0:
                prices.append(prices[-1] * 0.95)
            else:
                prices.append(prices[-1] * 1.05)
        result = self.detector.classify(prices)
        self.assertEqual(result.features["volatility_regime"], "elevated")

    def test_elevated_volume_detected(self):
        """Verify elevated volume is detected when recent volume exceeds long-term baseline."""
        prices = [100.0] * 45
        # Need 2x lookback_days volumes for long-term comparison
        volumes = [1000.0] * 40 + [2000.0] * 20
        detector = RegimeDetector(lookback_days=20)
        result = detector.classify(prices, volumes)
        self.assertEqual(result.features["volume_regime"], "elevated")
        self.assertGreater(result.features["volume_ratio"], 1.5)

    def test_affinity_scores_sum_to_one(self):
        """Verify regime affinity scores sum to 1.0."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        result = self.detector.classify(prices)
        self.assertAlmostEqual(sum(result.regime_affinity.values()), 1.0, places=5)

    def test_transition_probs_property_returns_affinity(self):
        """Verify backward-compatible transition_probs property returns regime_affinity."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        result = self.detector.classify(prices)
        self.assertIs(result.transition_probs, result.regime_affinity)

    def test_history_tracking(self):
        """Verify classification history is recorded."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        self.detector.classify(prices)
        history = self.detector.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][1], "R01")

    def test_clear_history(self):
        """Verify history can be cleared."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        self.detector.classify(prices)
        self.detector.clear_history()
        self.assertEqual(len(self.detector.get_history()), 0)

    def test_invalid_lookback_raises_error(self):
        """Verify ValueError for invalid lookback_days."""
        with self.assertRaises(ValueError):
            RegimeDetector(lookback_days=0)
        with self.assertRaises(ValueError):
            RegimeDetector(lookback_days=-1)

    def test_confidence_in_valid_range(self):
        """Verify confidence is always in [0.0, 1.0]."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        result = self.detector.classify(prices)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_regime_in_valid_set(self):
        """Verify classified regime is always in VALID_REGIMES."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        result = self.detector.classify(prices)
        self.assertIn(result.regime, [f"R{i:02d}" for i in range(1, 13)])

    def test_features_dict_contains_expected_keys(self):
        """Verify features dict contains all expected keys."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        result = self.detector.classify(prices)
        expected_keys = {
            "annualized_return",
            "annualized_volatility",
            "volume_ratio",
            "trend_strength",
            "trend_category",
            "volatility_regime",
            "volume_regime",
        }
        self.assertEqual(set(result.features.keys()), expected_keys)

    def test_zero_price_raises_error(self):
        """Verify zero price raises ValueError in classifier."""
        with self.assertRaises(ValueError):
            self.detector.classify([0.0, 100.0, 101.0])


class TestDetectRegimeConvenience(unittest.TestCase):
    """Test detect_regime() convenience function."""

    def test_convenience_function_returns_classification(self):
        """Verify detect_regime returns RegimeClassification."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        result = detect_regime(prices)
        self.assertIsInstance(result, RegimeClassification)
        self.assertIn(result.regime, [f"R{i:02d}" for i in range(1, 13)])

    def test_convenience_function_with_volumes(self):
        """Verify detect_regime works with volumes."""
        prices = [100.0 + i * 0.5 for i in range(25)]
        volumes = [1000.0] * 25
        result = detect_regime(prices, volumes)
        self.assertIsInstance(result, RegimeClassification)


if __name__ == "__main__":
    unittest.main()
