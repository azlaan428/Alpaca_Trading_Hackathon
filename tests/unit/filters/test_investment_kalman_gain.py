"""Adversarial unit test suite for investment_kalman_gain.py.

Verifies mathematical properties of effective measurement noise R_t and investment Kalman gain K_t
according to Proposition 3.1 (Team-Mates) and Theorem 2.4 (Public Judges).
"""

import math
import unittest
from investment_agent.filters.investment_kalman_gain import (
    compute_effective_measurement_noise,
    compute_investment_kalman_gain,
)


class TestEffectiveMeasurementNoise(unittest.TestCase):
    """Test compute_effective_measurement_noise R_t calculations, bounds, and limits."""

    def test_effective_measurement_noise_normal_case(self):
        # R_t = 1.0 * (1 - 0.5)/0.5 + 0.5^2 * 1.0 = 1.0 + 0.25 = 1.25
        r_t = compute_effective_measurement_noise(effective_confidence=0.5, disagreement=0.5, sigma_base_squared=1.0)
        self.assertAlmostEqual(r_t, 1.25, places=6)

    def test_zero_confidence_returns_infinity(self):
        """c_bar_t == 0.0 returns math.inf per Public Judges Definition 2.3."""
        r_t = compute_effective_measurement_noise(effective_confidence=0.0, disagreement=0.0, sigma_base_squared=1.0)
        self.assertTrue(math.isinf(r_t))

    def test_full_confidence_zero_disagreement_returns_zero(self):
        """c_bar_t == 1.0 and D_t == 0.0 returns R_t == 0.0."""
        r_t = compute_effective_measurement_noise(effective_confidence=1.0, disagreement=0.0, sigma_base_squared=1.0)
        self.assertEqual(r_t, 0.0)

    def test_reject_boolean_inputs(self):
        with self.assertRaises(TypeError):
            compute_effective_measurement_noise(effective_confidence=True, disagreement=0.5)
        with self.assertRaises(TypeError):
            compute_effective_measurement_noise(effective_confidence=0.5, disagreement=False)

    def test_reject_nan_and_inf_inputs(self):
        with self.assertRaises(ValueError):
            compute_effective_measurement_noise(effective_confidence=math.nan, disagreement=0.5)
        with self.assertRaises(ValueError):
            compute_effective_measurement_noise(effective_confidence=0.5, disagreement=math.inf)

    def test_reject_out_of_bounds_inputs(self):
        with self.assertRaises(ValueError):
            compute_effective_measurement_noise(effective_confidence=-0.1, disagreement=0.5)
        with self.assertRaises(ValueError):
            compute_effective_measurement_noise(effective_confidence=1.1, disagreement=0.5)
        with self.assertRaises(ValueError):
            compute_effective_measurement_noise(effective_confidence=0.5, disagreement=-0.1)
        with self.assertRaises(ValueError):
            compute_effective_measurement_noise(effective_confidence=0.5, disagreement=2.1)
        with self.assertRaises(ValueError):
            compute_effective_measurement_noise(effective_confidence=0.5, disagreement=0.5, sigma_base_squared=0.0)


class TestInvestmentKalmanGain(unittest.TestCase):
    """Test Proposition 3.1 (Team-Mates) / Theorem 2.4 (Public Judges) K_t properties."""

    def test_proposition_3_1_property_1_bounds_and_boundary_case(self):
        """Property 1: K_t in [0.0, 1.0]. Flag exact 1.0 boundary when R_t == 0."""
        k_normal = compute_investment_kalman_gain(prediction_covariance=1.0, effective_confidence=0.8, disagreement=0.2)
        self.assertTrue(0.0 <= k_normal <= 1.0)

        # Boundary case: c_bar_t = 1.0, D_t = 0.0 -> R_t = 0.0 -> K_t = P/(P+0) = 1.0 exactly.
        # Note: Proposition 3.1 states K_t in [0, 1), but at exact boundary c_bar=1.0 & D_t=0.0, K_t equals 1.0.
        k_boundary = compute_investment_kalman_gain(prediction_covariance=1.0, effective_confidence=1.0, disagreement=0.0)
        self.assertEqual(k_boundary, 1.0)

    def test_proposition_3_1_property_2_approaches_one(self):
        """Property 2: K_t -> 1 as c_bar_t -> 1^- and D_t -> 0^+."""
        k_limit = compute_investment_kalman_gain(prediction_covariance=1.0, effective_confidence=0.9999, disagreement=0.0001)
        self.assertAlmostEqual(k_limit, 1.0, delta=0.001)

    def test_proposition_3_1_property_3_approaches_zero(self):
        """Property 3: K_t -> 0 as c_bar_t -> 0^+ or D_t increases toward 2.0."""
        # Zero confidence limit (R_t = inf -> K_t = 0.0)
        k_zero_conf = compute_investment_kalman_gain(prediction_covariance=1.0, effective_confidence=0.0, disagreement=0.0)
        self.assertEqual(k_zero_conf, 0.0)

        # Increasing disagreement suppresses K_t
        k_low_disag = compute_investment_kalman_gain(prediction_covariance=1.0, effective_confidence=0.8, disagreement=0.1)
        k_high_disag = compute_investment_kalman_gain(prediction_covariance=1.0, effective_confidence=0.8, disagreement=2.0)
        self.assertLess(k_high_disag, k_low_disag)

    def test_proposition_3_1_property_4_monotonicity(self):
        """Property 4: K_t is strictly decreasing in R_t and strictly increasing in prediction_covariance."""
        # Monotonicity in prediction_covariance (P_pred)
        k_low_p = compute_investment_kalman_gain(prediction_covariance=0.5, effective_confidence=0.8, disagreement=0.5)
        k_high_p = compute_investment_kalman_gain(prediction_covariance=2.0, effective_confidence=0.8, disagreement=0.5)
        self.assertLess(k_low_p, k_high_p)

        # Monotonicity in effective_confidence (higher c_bar -> lower R_t -> higher K_t)
        k_low_c = compute_investment_kalman_gain(prediction_covariance=1.0, effective_confidence=0.3, disagreement=0.5)
        k_high_c = compute_investment_kalman_gain(prediction_covariance=1.0, effective_confidence=0.9, disagreement=0.5)
        self.assertLess(k_low_c, k_high_c)

    def test_reject_invalid_prediction_covariance(self):
        with self.assertRaises(ValueError):
            compute_investment_kalman_gain(prediction_covariance=0.0, effective_confidence=0.8, disagreement=0.2)
        with self.assertRaises(ValueError):
            compute_investment_kalman_gain(prediction_covariance=-1.0, effective_confidence=0.8, disagreement=0.2)


if __name__ == "__main__":
    unittest.main()
