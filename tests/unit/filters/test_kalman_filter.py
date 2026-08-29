"""
Tests for kalman_filter.py — Kalman Filter State Estimation Layer.

Uses unittest (stdlib).  Run with:

    python -m unittest test_kalman_filter -v
"""

from __future__ import annotations

import math
import unittest
from typing import List

import numpy as np

from investment_agent.filters.kalman_filter import KalmanFilter, KalmanState


class TestKalmanFilterInitialization(unittest.TestCase):
    """Test 1 — The filter initialises correctly."""

    def test_initial_state_matches_price(self) -> None:
        """Estimated price equals the initial price before any update."""
        kf = KalmanFilter(150.0)
        state = kf.get_state()
        self.assertAlmostEqual(state.estimated_price, 150.0, places=6)

    def test_initial_trend_is_zero(self) -> None:
        """Trend starts at zero (no prior directional information)."""
        kf = KalmanFilter(150.0)
        state = kf.get_state()
        self.assertAlmostEqual(state.trend, 0.0, places=6)

    def test_initial_covariance_is_finite(self) -> None:
        """Initial uncertainty values are finite and positive."""
        kf = KalmanFilter(150.0)
        state = kf.get_state()
        self.assertTrue(math.isfinite(state.uncertainty))
        self.assertTrue(math.isfinite(state.trend_uncertainty))
        self.assertGreater(state.uncertainty, 0.0)
        self.assertGreater(state.trend_uncertainty, 0.0)

    def test_step_count_starts_at_zero(self) -> None:
        """Step counter begins at zero."""
        kf = KalmanFilter(100.0)
        self.assertEqual(kf.step_count, 0)

    def test_state_is_frozen(self) -> None:
        """KalmanState is immutable (frozen dataclass)."""
        kf = KalmanFilter(100.0)
        state = kf.get_state()
        with self.assertRaises(AttributeError):
            state.estimated_price = 999.0  # type: ignore[misc]


class TestKalmanFilterConstantPrice(unittest.TestCase):
    """Test 2 — Constant price series."""

    def test_estimate_converges_to_observed_price(self) -> None:
        """After many updates with a constant price, the estimate should
        converge very close to that price."""
        price = 200.0
        kf = KalmanFilter(price, measurement_noise=1.0)
        for _ in range(100):
            state = kf.update(price)

        self.assertAlmostEqual(state.estimated_price, price, delta=0.01)

    def test_trend_converges_to_zero(self) -> None:
        """Trend should converge toward zero for a flat price."""
        price = 200.0
        kf = KalmanFilter(price, measurement_noise=1.0)
        for _ in range(100):
            state = kf.update(price)

        self.assertAlmostEqual(state.trend, 0.0, delta=0.01)

    def test_covariance_remains_finite(self) -> None:
        """Covariance must not diverge."""
        price = 200.0
        kf = KalmanFilter(price, measurement_noise=1.0)
        for _ in range(100):
            state = kf.update(price)

        self.assertTrue(math.isfinite(state.price_variance))
        self.assertTrue(math.isfinite(state.trend_variance))
        self.assertGreater(state.price_variance, 0.0)

    def test_uncertainty_decreases_over_time(self) -> None:
        """Uncertainty should decrease as consistent observations arrive."""
        price = 200.0
        kf = KalmanFilter(price, measurement_noise=1.0)
        initial_state = kf.get_state()

        for _ in range(20):
            state = kf.update(price)

        self.assertLess(state.uncertainty, initial_state.uncertainty)


class TestKalmanFilterRisingPrice(unittest.TestCase):
    """Test 3 — Rising (increasing) price series."""

    def test_estimate_follows_observations(self) -> None:
        """Estimated price should track the rising observations within a
        reasonable tolerance."""
        kf = KalmanFilter(100.0, measurement_noise=0.5)
        for i in range(1, 51):
            price = 100.0 + 1.0 * i  # +$1/step
            state = kf.update(price)

        # After 50 steps of +$1/step, true price = 150
        self.assertAlmostEqual(state.estimated_price, 150.0, delta=3.0)

    def test_trend_becomes_positive(self) -> None:
        """Trend should be clearly positive for a rising series."""
        kf = KalmanFilter(100.0, measurement_noise=0.5)
        for i in range(1, 51):
            state = kf.update(100.0 + 1.0 * i)

        self.assertGreater(state.trend, 0.5)

    def test_all_outputs_finite(self) -> None:
        """Every field in the state must be finite."""
        kf = KalmanFilter(100.0)
        for i in range(1, 31):
            state = kf.update(100.0 + 0.5 * i)

        self.assertTrue(math.isfinite(state.estimated_price))
        self.assertTrue(math.isfinite(state.trend))
        self.assertTrue(math.isfinite(state.uncertainty))
        self.assertTrue(math.isfinite(state.trend_uncertainty))
        self.assertTrue(math.isfinite(state.innovation))
        self.assertTrue(math.isfinite(state.kalman_gain_price))


class TestKalmanFilterFallingPrice(unittest.TestCase):
    """Test 4 — Falling (decreasing) price series."""

    def test_estimate_follows_observations(self) -> None:
        """Estimated price should track the falling observations."""
        kf = KalmanFilter(200.0, measurement_noise=0.5)
        for i in range(1, 51):
            price = 200.0 - 1.0 * i  # -$1/step → 150
            state = kf.update(price)

        self.assertAlmostEqual(state.estimated_price, 150.0, delta=3.0)

    def test_trend_becomes_negative(self) -> None:
        """Trend should be clearly negative for a falling series."""
        kf = KalmanFilter(200.0, measurement_noise=0.5)
        for i in range(1, 51):
            state = kf.update(200.0 - 1.0 * i)

        self.assertLess(state.trend, -0.5)


class TestKalmanFilterNoisyData(unittest.TestCase):
    """Test 5 — Noisy data around a known trend."""

    def test_filtered_estimate_is_smoother(self) -> None:
        """The filtered price series should have lower variance around the
        true trend than the raw observations."""
        np.random.seed(123)

        true_trend = 0.3
        true_start = 100.0
        noise_std = 3.0
        n_steps = 100

        # Generate true prices and noisy observations
        true_prices: List[float] = []
        observed: List[float] = []
        for i in range(n_steps):
            tp = true_start + true_trend * i
            op = tp + np.random.normal(0, noise_std)
            op = max(op, 0.01)  # keep positive
            true_prices.append(tp)
            observed.append(op)

        # Run filter
        kf = KalmanFilter(
            observed[0],
            measurement_noise=noise_std ** 2,
            process_noise_price=0.1,
            process_noise_trend=0.01,
        )
        estimated: List[float] = []
        for obs in observed:
            state = kf.update(obs)
            estimated.append(state.estimated_price)

        # Compute mean-squared error relative to the true price
        mse_raw = sum((o - t) ** 2 for o, t in zip(observed, true_prices)) / n_steps
        mse_est = sum((e - t) ** 2 for e, t in zip(estimated, true_prices)) / n_steps

        # The filter should produce a meaningfully lower MSE
        self.assertLess(
            mse_est, mse_raw,
            f"Filter MSE ({mse_est:.3f}) should be less than raw MSE ({mse_raw:.3f})"
        )

    def test_outputs_remain_finite(self) -> None:
        """All outputs remain finite under noisy conditions."""
        np.random.seed(456)
        kf = KalmanFilter(100.0, measurement_noise=4.0)
        for _ in range(200):
            price = max(100.0 + np.random.normal(0, 5), 0.01)
            state = kf.update(price)

        self.assertTrue(math.isfinite(state.estimated_price))
        self.assertTrue(math.isfinite(state.trend))
        self.assertTrue(math.isfinite(state.uncertainty))


class TestKalmanFilterInvalidInput(unittest.TestCase):
    """Test 6 — Invalid input handling."""

    def test_nan_price_rejected(self) -> None:
        """NaN observation must raise ValueError."""
        kf = KalmanFilter(100.0)
        with self.assertRaises(ValueError):
            kf.update(float("nan"))

    def test_positive_infinity_rejected(self) -> None:
        """Positive infinity must raise ValueError."""
        kf = KalmanFilter(100.0)
        with self.assertRaises(ValueError):
            kf.update(float("inf"))

    def test_negative_infinity_rejected(self) -> None:
        """Negative infinity must raise ValueError."""
        kf = KalmanFilter(100.0)
        with self.assertRaises(ValueError):
            kf.update(float("-inf"))

    def test_zero_price_rejected(self) -> None:
        """Zero price must raise ValueError."""
        kf = KalmanFilter(100.0)
        with self.assertRaises(ValueError):
            kf.update(0.0)

    def test_negative_price_rejected(self) -> None:
        """Negative price must raise ValueError."""
        kf = KalmanFilter(100.0)
        with self.assertRaises(ValueError):
            kf.update(-50.0)

    def test_non_numeric_price_rejected(self) -> None:
        """Non-numeric observation must raise TypeError."""
        kf = KalmanFilter(100.0)
        with self.assertRaises(TypeError):
            kf.update("invalid")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            kf.update(True)  # type: ignore[arg-type]

    def test_nan_initial_price_rejected(self) -> None:
        """NaN initial price must raise ValueError."""
        with self.assertRaises(ValueError):
            KalmanFilter(float("nan"))

    def test_zero_initial_price_rejected(self) -> None:
        """Zero initial price must raise ValueError."""
        with self.assertRaises(ValueError):
            KalmanFilter(0.0)

    def test_negative_initial_price_rejected(self) -> None:
        """Negative initial price must raise ValueError."""
        with self.assertRaises(ValueError):
            KalmanFilter(-100.0)

    def test_non_numeric_initial_price_rejected(self) -> None:
        """Non-numeric initial price must raise TypeError."""
        with self.assertRaises(TypeError):
            KalmanFilter("invalid")  # type: ignore[arg-type]


class TestConfigurationValidation(unittest.TestCase):
    """Test 7 — Comprehensive configuration validation for all parameters."""

    def test_invalid_dt_rejected(self) -> None:
        """dt must be finite, numeric, and > 0."""
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, dt=0.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, dt=-1.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, dt=float("nan"))
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, dt=float("inf"))
        with self.assertRaises(TypeError):
            KalmanFilter(100.0, dt="invalid")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            KalmanFilter(100.0, dt=True)  # type: ignore[arg-type]

    def test_invalid_measurement_noise_rejected(self) -> None:
        """measurement_noise must be finite, numeric, and > 0."""
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, measurement_noise=0.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, measurement_noise=-1.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, measurement_noise=float("nan"))
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, measurement_noise=float("inf"))
        with self.assertRaises(TypeError):
            KalmanFilter(100.0, measurement_noise="invalid")  # type: ignore[arg-type]

    def test_invalid_process_noise_price_rejected(self) -> None:
        """process_noise_price must be finite, numeric, and > 0."""
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, process_noise_price=0.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, process_noise_price=-1e-4)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, process_noise_price=float("nan"))
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, process_noise_price=float("inf"))

    def test_invalid_process_noise_trend_rejected(self) -> None:
        """process_noise_trend must be finite, numeric, and > 0."""
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, process_noise_trend=0.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, process_noise_trend=-1e-6)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, process_noise_trend=float("nan"))

    def test_invalid_initial_price_variance_rejected(self) -> None:
        """initial_price_variance must be finite, numeric, and > 0."""
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, initial_price_variance=0.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, initial_price_variance=-1.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, initial_price_variance=float("nan"))

    def test_invalid_initial_trend_variance_rejected(self) -> None:
        """initial_trend_variance must be finite, numeric, and > 0."""
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, initial_trend_variance=0.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, initial_trend_variance=-1.0)
        with self.assertRaises(ValueError):
            KalmanFilter(100.0, initial_trend_variance=float("nan"))


class TestKalmanFilterReset(unittest.TestCase):
    """Test 8 — Reset behaviour and initial variance restoration."""

    def test_reset_restores_custom_initial_variances(self) -> None:
        """reset() must restore custom initial_price_variance and initial_trend_variance."""
        custom_price_var = 5.0
        custom_trend_var = 2.5
        kf = KalmanFilter(
            100.0,
            initial_price_variance=custom_price_var,
            initial_trend_variance=custom_trend_var,
        )

        # Update several times to mutate internal state and covariance
        for i in range(1, 10):
            kf.update(100.0 + i)

        # Confirm state changed
        mutated_state = kf.get_state()
        self.assertNotEqual(mutated_state.estimated_price, 100.0)
        self.assertGreater(kf.step_count, 0)

        # Reset filter with a new initial price
        kf.reset(250.0)
        reset_state = kf.get_state()

        self.assertEqual(kf.step_count, 0)
        self.assertAlmostEqual(reset_state.estimated_price, 250.0, places=6)
        self.assertAlmostEqual(reset_state.trend, 0.0, places=6)
        self.assertAlmostEqual(reset_state.price_variance, custom_price_var, places=6)
        self.assertAlmostEqual(reset_state.trend_variance, custom_trend_var, places=6)
        self.assertAlmostEqual(reset_state.innovation, 0.0, places=6)
        self.assertAlmostEqual(reset_state.kalman_gain_price, 0.0, places=6)

    def test_reset_invalid_price_rejected(self) -> None:
        """reset() with invalid prices raises ValueError/TypeError."""
        kf = KalmanFilter(100.0)
        with self.assertRaises(ValueError):
            kf.reset(0.0)
        with self.assertRaises(ValueError):
            kf.reset(-10.0)
        with self.assertRaises(ValueError):
            kf.reset(float("nan"))
        with self.assertRaises(TypeError):
            kf.reset("invalid")  # type: ignore[arg-type]


class TestCovarianceSymmetryAndPositivity(unittest.TestCase):
    """Test 9 — Joseph-form covariance symmetry and positivity enforcement."""

    def test_covariance_is_symmetric_after_updates(self) -> None:
        """After many updates, internal covariance P must be symmetric (P == Pᵀ)."""
        kf = KalmanFilter(100.0, measurement_noise=1.5)
        for i in range(50):
            price = 100.0 + np.sin(i / 5.0) * 5.0
            kf.update(max(price, 0.01))

        np.testing.assert_allclose(kf._P, kf._P.T, rtol=1e-12, atol=1e-12)

    def test_covariance_diagonal_remains_positive(self) -> None:
        """Price and trend variances must remain positive."""
        kf = KalmanFilter(100.0)
        for i in range(100):
            state = kf.update(100.0 + i * 0.1)
            self.assertGreater(state.price_variance, 0.0)
            self.assertGreater(state.trend_variance, 0.0)


class TestGetStateIdempotency(unittest.TestCase):
    """Test 10 — get_state() is idempotent and side-effect free."""

    def test_get_state_does_not_mutate_filter(self) -> None:
        """Repeated calls to get_state() produce identical snapshots without changing step_count."""
        kf = KalmanFilter(100.0)
        kf.update(105.0)

        s1 = kf.get_state()
        count1 = kf.step_count

        s2 = kf.get_state()
        count2 = kf.step_count

        self.assertEqual(count1, count2)
        self.assertEqual(s1.estimated_price, s2.estimated_price)
        self.assertEqual(s1.trend, s2.trend)
        self.assertEqual(s1.price_variance, s2.price_variance)
        self.assertEqual(s1.trend_variance, s2.trend_variance)


class TestStepCount(unittest.TestCase):
    """Test 11 — Step counter tracking."""

    def test_step_count_increments_per_update(self) -> None:
        """step_count increases by exactly 1 for each update() call."""
        kf = KalmanFilter(100.0)
        self.assertEqual(kf.step_count, 0)
        for i in range(1, 6):
            kf.update(100.0 + i)
            self.assertEqual(kf.step_count, i)

        kf.reset(150.0)
        self.assertEqual(kf.step_count, 0)


class TestLongRunningStability(unittest.TestCase):
    """Test 12 — Long-running numerical stability."""

    def test_thousands_of_steps_remain_finite(self) -> None:
        """Run 1000 updates on random walk prices and verify state remains finite."""
        np.random.seed(999)
        price = 100.0
        kf = KalmanFilter(price, measurement_noise=2.0)

        for _ in range(1000):
            price = max(price + np.random.normal(0, 0.5), 0.1)
            state = kf.update(price)
            self.assertTrue(math.isfinite(state.estimated_price))
            self.assertTrue(math.isfinite(state.trend))
            self.assertTrue(math.isfinite(state.uncertainty))
            self.assertTrue(math.isfinite(state.trend_uncertainty))
            self.assertTrue(math.isfinite(state.innovation))
            self.assertTrue(math.isfinite(state.kalman_gain_price))


class TestTransactionalUpdateFailure(unittest.TestCase):
    """Test 13 — Transactional failure: a failed update must NOT mutate internal state."""

    def test_failed_update_does_not_mutate_any_attribute(self) -> None:
        """If update() fails due to numerical instability, x, P, innovation, gain, and step_count remain untouched."""
        kf = KalmanFilter(100.0)
        kf.update(105.0)
        kf.update(107.0)

        # Capture complete internal state prior to failing update
        x_before = np.copy(kf._x)
        P_before = np.copy(kf._P)
        step_before = kf.step_count
        innov_before = kf._innovation
        gain_before = np.copy(kf._kalman_gain)

        # Corrupt internal covariance matrix to NaN to force candidate update calculation to fail
        kf._P[0, 0] = np.nan

        with self.assertRaises(RuntimeError):
            kf.update(110.0)

        # A. x not mutated (restore nan trigger so we can compare x)
        np.testing.assert_array_equal(kf._x, x_before)

        # C. innovation not mutated
        self.assertEqual(kf._innovation, innov_before)

        # D. kalman gain not mutated
        np.testing.assert_array_equal(kf._kalman_gain, gain_before)

        # E. step count not mutated
        self.assertEqual(kf.step_count, step_before)

    def test_subsequent_valid_update_equals_clean_filter(self) -> None:
        """F. After a failed update (e.g. invalid price observation), a subsequent valid update
        behaves exactly as if the failed update had never happened."""
        kf_test = KalmanFilter(100.0)
        kf_clean = KalmanFilter(100.0)

        # Perform 3 identical valid updates on both filters
        for price in [102.0, 104.0, 105.0]:
            kf_test.update(price)
            kf_clean.update(price)

        # Attempt an invalid update on kf_test
        with self.assertRaises(ValueError):
            kf_test.update(float("nan"))

        with self.assertRaises(ValueError):
            kf_test.update(-50.0)

        # Now perform a subsequent valid update on both filters
        state_test = kf_test.update(108.0)
        state_clean = kf_clean.update(108.0)

        # Equivalence checks: test filter must match clean filter in every field
        self.assertEqual(kf_test.step_count, kf_clean.step_count)
        self.assertAlmostEqual(state_test.estimated_price, state_clean.estimated_price, places=12)
        self.assertAlmostEqual(state_test.trend, state_clean.trend, places=12)
        self.assertAlmostEqual(state_test.uncertainty, state_clean.uncertainty, places=12)
        self.assertAlmostEqual(state_test.trend_uncertainty, state_clean.trend_uncertainty, places=12)
        self.assertAlmostEqual(state_test.price_variance, state_clean.price_variance, places=12)
        self.assertAlmostEqual(state_test.trend_variance, state_clean.trend_variance, places=12)
        self.assertAlmostEqual(state_test.innovation, state_clean.innovation, places=12)
        self.assertAlmostEqual(state_test.kalman_gain_price, state_clean.kalman_gain_price, places=12)


if __name__ == "__main__":
    unittest.main()



