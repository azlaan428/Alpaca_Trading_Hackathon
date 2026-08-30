"""Comprehensive unit tests for HMM inference engine and regime detector.

Tests:
- Forward-backward algorithm
- Viterbi decoding
- Dwell-time enforcement
- Entropy calculation
- Emission probabilities
- Parameter validation
- Regime detector integration
"""

import math
import unittest
from typing import List

import numpy as np

from investment_agent.regimes.hmm_inference import (
    HMMParameters,
    HMMInference,
    HMMInferenceResult,
    HMMRegimeDetectorImpl,
    load_hmm_parameters,
    N_STATES,
    N_FEATURES,
    MIN_DWELL_BARS,
)
from investment_agent.regimes.hmm_regime_detector import (
    HMMRegimeDetector,
    RegimeProbability,
    get_hmm_detector,
    _load_regime_config,
)
from investment_agent.regimes.regimes import VALID_REGIMES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_test_params() -> HMMParameters:
    """Create simple test HMM parameters."""
    N = N_STATES
    # Simple transition matrix: high diagonal, small off-diagonal
    A = np.ones((N, N)) * 0.01
    for i in range(N):
        A[i, i] = 0.89
    # Normalize rows
    A /= A.sum(axis=1, keepdims=True)

    # Uniform prior
    pi = np.ones(N) / N

    # Distinct emission means for each state
    means = np.zeros((N, N_FEATURES))
    for i in range(N):
        means[i, :] = i * 0.1  # Each state has distinct mean

    # Unit variance
    covs = np.ones((N, N_FEATURES))

    return HMMParameters(
        transition_matrix=A,
        prior=pi,
        emission_means=means,
        emission_covariances=covs,
    )


def make_test_observations(T: int = 10) -> np.ndarray:
    """Create test observation sequence."""
    np.random.seed(42)
    return np.random.randn(T, N_FEATURES).astype(np.float64)


# ---------------------------------------------------------------------------
# Test HMM Parameters
# ---------------------------------------------------------------------------

class TestHMMParameters(unittest.TestCase):
    """Test HMM parameter validation."""

    def test_valid_parameters_created(self):
        """Verify valid HMM parameters can be created."""
        params = make_test_params()
        self.assertIsInstance(params, HMMParameters)

    def test_invalid_transition_shape_raises(self):
        """Verify wrong transition matrix shape raises ValueError."""
        with self.assertRaises(ValueError):
            HMMParameters(
                transition_matrix=np.eye(10),
                prior=np.ones(12) / 12,
                emission_means=np.zeros((12, 7)),
                emission_covariances=np.ones((12, 7)),
            )

    def test_non_stochastic_transition_raises(self):
        """Verify transition matrix rows must sum to 1."""
        with self.assertRaises(ValueError):
            HMMParameters(
                transition_matrix=np.ones((12, 12)) * 0.5,
                prior=np.ones(12) / 12,
                emission_means=np.zeros((12, 7)),
                emission_covariances=np.ones((12, 7)),
            )

    def test_invalid_prior_shape_raises(self):
        """Verify wrong prior shape raises ValueError."""
        with self.assertRaises(ValueError):
            HMMParameters(
                transition_matrix=np.ones((12, 12)) / 12,
                prior=np.ones(10) / 10,
                emission_means=np.zeros((12, 7)),
                emission_covariances=np.ones((12, 7)),
            )

    def test_invalid_prior_sum_raises(self):
        """Verify prior must sum to 1."""
        with self.assertRaises(ValueError):
            HMMParameters(
                transition_matrix=np.ones((12, 12)) / 12,
                prior=np.ones(12) * 0.5,
                emission_means=np.zeros((12, 7)),
                emission_covariances=np.ones((12, 7)),
            )


# ---------------------------------------------------------------------------
# Test Forward-Backward
# ---------------------------------------------------------------------------

class TestForwardBackward(unittest.TestCase):
    """Test forward-backward inference."""

    def test_forward_backward_runs(self):
        """Verify forward-backward produces valid posteriors."""
        params = make_test_params()
        inference = HMMInference(params)
        obs = make_test_observations(10)
        gamma, ll, alpha, beta = inference.forward_backward(obs)

        self.assertEqual(gamma.shape, (10, 12))
        self.assertEqual(alpha.shape, (10, 12))
        self.assertEqual(beta.shape, (10, 12))

        # Posteriors must sum to 1
        row_sums = gamma.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-10)

        # All probabilities in [0, 1]
        self.assertTrue(np.all(gamma >= 0.0))
        self.assertTrue(np.all(gamma <= 1.0))

    def test_forward_backward_log_likelihood(self):
        """Verify log-likelihood is computed correctly."""
        params = make_test_params()
        inference = HMMInference(params)
        obs = make_test_observations(10)
        gamma, ll, alpha, beta = inference.forward_backward(obs)

        self.assertTrue(math.isfinite(ll))
        self.assertIsInstance(ll, float)

    def test_single_observation(self):
        """Verify forward-backward works with single observation."""
        params = make_test_params()
        inference = HMMInference(params)
        obs = make_test_observations(1)
        gamma, ll, alpha, beta = inference.forward_backward(obs)

        self.assertEqual(gamma.shape, (1, 12))
        np.testing.assert_allclose(gamma[0, :].sum(), 1.0, atol=1e-10)


# ---------------------------------------------------------------------------
# Test Viterbi
# ---------------------------------------------------------------------------

class TestViterbi(unittest.TestCase):
    """Test Viterbi decoding."""

    def test_viterbi_returns_valid_path(self):
        """Verify Viterbi returns valid regime sequence."""
        params = make_test_params()
        inference = HMMInference(params)
        obs = make_test_observations(20)
        path = inference.viterbi(obs)

        self.assertEqual(len(path), 20)
        for regime in path:
            self.assertIn(regime, VALID_REGIMES)

    def test_viterbi_single_observation(self):
        """Verify Viterbi works with single observation."""
        params = make_test_params()
        inference = HMMInference(params)
        obs = make_test_observations(1)
        path = inference.viterbi(obs)

        self.assertEqual(len(path), 1)
        self.assertIn(path[0], VALID_REGIMES)


# ---------------------------------------------------------------------------
# Test Dwell-Time Enforcement
# ---------------------------------------------------------------------------

class TestDwellTimeEnforcement(unittest.TestCase):
    """Test dwell-time enforcement."""

    def test_dwell_time_blocks_short_runs(self):
        """Verify dwell-time blocks regime runs shorter than minimum."""
        inference = HMMInference(make_test_params())

        # Path with short runs (length 1)
        path = ["R01", "R02", "R01", "R02"]
        result = inference.enforce_dwell_time(path, min_dwell=3)

        # All short runs should be filled with previous regime
        # R01, R02, R01, R02 -> R01, R01, R01, R02 (first transition blocked)
        # Actually let's trace:
        # i=1: R02 != R01, check run length: j=2 (R01 != R02), run_length=1 < 3
        #   fill [1] with R01 -> path = [R01, R01, R01, R02]
        # i=3: R02 != R01, run length: j=4, run_length=1 < 3
        #   fill [3] with R01 -> path = [R01, R01, R01, R01]
        self.assertEqual(result, ["R01", "R01", "R01", "R01"])

    def test_dwell_time_preserves_long_runs(self):
        """Verify dwell-time preserves runs longer than minimum."""
        inference = HMMInference(make_test_params())

        # Path with long run (length 5 >= 3)
        path = ["R01"] * 5 + ["R02"] * 5
        result = inference.enforce_dwell_time(path, min_dwell=3)

        # Both runs should be preserved
        self.assertEqual(result[:5], ["R01"] * 5)
        self.assertEqual(result[5:], ["R02"] * 5)

    def test_dwell_time_single_value(self):
        """Verify single-value path is unchanged."""
        inference = HMMInference(make_test_params())
        path = ["R01"]
        result = inference.enforce_dwell_time(path, min_dwell=3)
        self.assertEqual(result, ["R01"])


# ---------------------------------------------------------------------------
# Test Entropy
# ---------------------------------------------------------------------------

class TestEntropy(unittest.TestCase):
    """Test entropy computation."""

    def test_entropy_computed(self):
        """Verify entropy is computed correctly."""
        inference = HMMInference(make_test_params())

        # Uniform distribution -> maximum entropy
        gamma = np.ones((1, 12)) / 12
        entropy, normalized, confident = inference.compute_entropy(gamma)

        expected_entropy = math.log(12)  # max entropy for 12 states
        self.assertAlmostEqual(entropy, expected_entropy, places=5)
        self.assertAlmostEqual(normalized, 1.0, places=5)
        self.assertFalse(confident)

    def test_zero_entropy(self):
        """Verify zero entropy for certain state."""
        inference = HMMInference(make_test_params())

        # Certain state -> zero entropy
        gamma = np.zeros((1, 12))
        gamma[0, 0] = 1.0
        entropy, normalized, confident = inference.compute_entropy(gamma)

        self.assertAlmostEqual(entropy, 0.0, places=5)
        self.assertAlmostEqual(normalized, 0.0, places=5)
        self.assertTrue(confident)

    def test_normalized_entropy_in_range(self):
        """Verify normalized entropy is in [0, 1]."""
        inference = HMMInference(make_test_params())
        obs = make_test_observations(10)
        gamma, _, _, _ = inference.forward_backward(obs)
        _, normalized, _ = inference.compute_entropy(gamma)

        self.assertGreaterEqual(normalized, 0.0)
        self.assertLessEqual(normalized, 1.0)


# ---------------------------------------------------------------------------
# Test HMM Regime Detector
# ---------------------------------------------------------------------------

class TestHMMRegimeDetector(unittest.TestCase):
    """Test HMMRegimeDetector class."""

    def setUp(self):
        """Create detector for each test."""
        self.detector = HMMRegimeDetector()

    def test_detector_initializes(self):
        """Verify detector initializes with config."""
        self.assertIsNotNone(self.detector)

    def test_classify_returns_regime_probability(self):
        """Verify classify returns RegimeProbability."""
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        result = self.detector.classify(features)
        self.assertIsInstance(result, RegimeProbability)

    def test_classify_regime_in_valid_set(self):
        """Verify classified regime is in VALID_REGIMES."""
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        result = self.detector.classify(features)
        self.assertIn(result.regime, VALID_REGIMES)

    def test_probabilities_sum_to_one(self):
        """Verify posterior probabilities sum to 1.0."""
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        result = self.detector.classify(features)
        total = sum(result.probabilities.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_all_probabilities_in_range(self):
        """Verify all probabilities are in [0, 1]."""
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        result = self.detector.classify(features)
        for prob in result.probabilities.values():
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)

    def test_multiple_observations(self):
        """Verify classify works with multiple observations."""
        features = [
            [50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5],
            [55.0, 0.5, 1.2, 22.0, 1.1, 0.6, 0.52],
            [60.0, 1.0, 1.5, 25.0, 1.3, 0.7, 0.55],
        ]
        result = self.detector.classify(features)
        self.assertIn(result.regime, VALID_REGIMES)

    def test_insufficient_features_raises(self):
        """Verify ValueError for wrong feature count."""
        with self.assertRaises(ValueError):
            self.detector.classify([[50.0, 0.0]])  # Only 2 features

    def test_dwell_time_from_config(self):
        """Verify dwell time is loaded from config."""
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        result = self.detector.classify(features)
        self.assertGreaterEqual(result.dwell_time, 2)
        self.assertLessEqual(result.dwell_time, 3)


# ---------------------------------------------------------------------------
# Test HMM Config Loading
# ---------------------------------------------------------------------------

class TestHMMConfigLoading(unittest.TestCase):
    """Test HMM configuration loading."""

    def test_config_has_regimes(self):
        """Verify config has regimes section."""
        config = _load_regime_config()
        if config:
            self.assertIn("regimes", config)

    def test_config_has_priors(self):
        """Verify config has priors section."""
        config = _load_regime_config()
        if config:
            self.assertIn("priors", config)

    def test_config_has_emission_means(self):
        """Verify config has emission means."""
        config = _load_regime_config()
        if config:
            self.assertIn("emission_mean", config)

    def test_config_has_dwell_times(self):
        """Verify config has dwell times."""
        config = _load_regime_config()
        if config:
            self.assertIn("min_dwell_bars", config)


# ---------------------------------------------------------------------------
# Test Provenance
# ---------------------------------------------------------------------------

class TestHMMProvenance(unittest.TestCase):
    """Test HMM detector provenance and history."""

    def test_history_tracking(self):
        """Verify classification history is recorded."""
        detector = HMMRegimeDetector()
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        detector.classify(features)
        history = detector.get_history()
        self.assertEqual(len(history), 1)

    def test_clear_history(self):
        """Verify history can be cleared."""
        detector = HMMRegimeDetector()
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        detector.classify(features)
        detector.clear_history()
        self.assertEqual(len(detector.get_history()), 0)


class TestStrictInputValidation(unittest.TestCase):
    """Test strict input validation for HMM inference."""

    def test_nan_features_raise_error(self):
        """Verify NaN in features raises ValueError."""
        detector = HMMRegimeDetector()
        with self.assertRaises(ValueError) as ctx:
            detector.classify([[50.0, float("nan"), 1.0, 20.0, 1.0, 0.5, 0.5]])
        self.assertIn("NaN", str(ctx.exception))

    def test_inf_features_raise_error(self):
        """Verify Infinity in features raises ValueError."""
        detector = HMMRegimeDetector()
        with self.assertRaises(ValueError) as ctx:
            detector.classify([[50.0, 0.0, float("inf"), 20.0, 1.0, 0.5, 0.5]])
        self.assertIn("Infinity", str(ctx.exception))

    def test_wrong_feature_count_raises_error(self):
        """Verify wrong number of features raises ValueError."""
        detector = HMMRegimeDetector()
        with self.assertRaises(ValueError) as ctx:
            detector.classify([[50.0, 0.0]])
        self.assertIn("7 features", str(ctx.exception))

    def test_empty_sequence_raises_error(self):
        """Verify empty feature sequence raises ValueError."""
        detector = HMMRegimeDetector()
        with self.assertRaises(ValueError) as ctx:
            detector.classify([])
        self.assertIn("Expected 7 features", str(ctx.exception))


class TestHMMParameterValidation(unittest.TestCase):
    """Test HMM parameter validation edge cases."""

    def test_negative_transition_probability_raises(self):
        """Verify negative transition probabilities raise ValueError."""
        A = np.ones((12, 12)) / 12
        A[0, 0] = -0.1  # negative value
        # Compensate to keep row sum = 1.0
        A[0, 1] = 1.0 - (-0.1) - 10 * (1/12)
        with self.assertRaises(ValueError) as ctx:
            HMMParameters(
                transition_matrix=A,
                prior=np.ones(12) / 12,
                emission_means=np.zeros((12, 7)),
                emission_covariances=np.ones((12, 7)),
            )
        self.assertIn("negative", str(ctx.exception))

    def test_nan_transition_raises(self):
        """Verify NaN in transition matrix raises ValueError."""
        A = np.ones((12, 12)) / 12
        A[0, 0] = float("nan")
        with self.assertRaises(ValueError) as ctx:
            HMMParameters(
                transition_matrix=A,
                prior=np.ones(12) / 12,
                emission_means=np.zeros((12, 7)),
                emission_covariances=np.ones((12, 7)),
            )
        self.assertIn("NaN", str(ctx.exception))

    def test_zero_covariance_raises(self):
        """Verify zero covariance raises ValueError."""
        covs = np.ones((12, 7))
        covs[0, 0] = 0.0
        with self.assertRaises(ValueError) as ctx:
            HMMParameters(
                transition_matrix=np.ones((12, 12)) / 12,
                prior=np.ones(12) / 12,
                emission_means=np.zeros((12, 7)),
                emission_covariances=covs,
            )
        self.assertIn("strictly positive", str(ctx.exception))

    def test_negative_covariance_raises(self):
        """Verify negative covariance raises ValueError."""
        covs = np.ones((12, 7))
        covs[0, 0] = -1.0
        with self.assertRaises(ValueError) as ctx:
            HMMParameters(
                transition_matrix=np.ones((12, 12)) / 12,
                prior=np.ones(12) / 12,
                emission_means=np.zeros((12, 7)),
                emission_covariances=covs,
            )
        self.assertIn("strictly positive", str(ctx.exception))

    def test_zero_transition_probability_raises(self):
        """Verify zero transition probabilities raise ValueError."""
        A = np.ones((12, 12)) / 12
        A[0, 1] = 0.0  # zero transition
        # Compensate to keep row sum = 1.0
        A[0, 2] = 1.0 - 10 * (1/12)
        with self.assertRaises(ValueError) as ctx:
            HMMParameters(
                transition_matrix=A,
                prior=np.ones(12) / 12,
                emission_means=np.zeros((12, 7)),
                emission_covariances=np.ones((12, 7)),
            )
        self.assertIn("zero probabilities", str(ctx.exception))

    def test_zero_prior_probability_raises(self):
        """Verify zero prior probabilities raise ValueError."""
        prior = np.ones(12) / 12
        prior[0] = 0.0  # zero prior
        # Compensate to keep sum = 1.0
        prior[1] = 1.0 - 10 * (1/12)
        with self.assertRaises(ValueError) as ctx:
            HMMParameters(
                transition_matrix=np.ones((12, 12)) / 12,
                prior=prior,
                emission_means=np.zeros((12, 7)),
                emission_covariances=np.ones((12, 7)),
            )
        self.assertIn("zero probabilities", str(ctx.exception))

    def test_arrays_are_readonly(self):
        """Verify NumPy arrays in HMMParameters are read-only."""
        params = make_test_params()
        with self.assertRaises(ValueError):
            params.transition_matrix[0, 0] = 0.5
        with self.assertRaises(ValueError):
            params.prior[0] = 0.5
        with self.assertRaises(ValueError):
            params.emission_means[0, 0] = 0.5
        with self.assertRaises(ValueError):
            params.emission_covariances[0, 0] = 0.5


class TestRegimeProbabilityNormalizedEntropy(unittest.TestCase):
    """Test that RegimeProbability exposes normalized_entropy."""

    def test_normalized_entropy_in_range(self):
        """Verify normalized_entropy is in [0, 1]."""
        detector = HMMRegimeDetector()
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        result = detector.classify(features)
        self.assertIsInstance(result, RegimeProbability)
        self.assertTrue(hasattr(result, "normalized_entropy"))
        self.assertGreaterEqual(result.normalized_entropy, 0.0)
        self.assertLessEqual(result.normalized_entropy, 1.0)

    def test_normalized_entropy_matches_hmm_result(self):
        """Verify normalized_entropy matches HMMInferenceResult."""
        detector = HMMRegimeDetector()
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        result = detector.classify(features)
        history = detector.get_history()
        self.assertEqual(len(history), 1)
        self.assertAlmostEqual(
            result.normalized_entropy,
            history[0].normalized_entropy,
            places=5,
        )


class TestDwellTimeTransitions(unittest.TestCase):
    """Test dwell-time transition behavior."""

    def test_dwell_time_blocks_short_runs(self):
        """Verify dwell-time blocks regime runs shorter than minimum."""
        from investment_agent.regimes.hmm_inference import HMMInference
        inference = HMMInference(make_test_params())
        
        # Path with short runs: R01,R01,R02,R01
        # R01 (stay), R01 (stay), R02 (new, run_length=1<3, fill with R01), R01 (stay)
        path = ["R01", "R01", "R02", "R01"]
        result = inference.enforce_dwell_time(path, min_dwell=3)
        self.assertEqual(result, ["R01", "R01", "R01", "R01"])

    def test_dwell_time_preserves_long_runs(self):
        """Verify dwell-time preserves runs longer than minimum."""
        from investment_agent.regimes.hmm_inference import HMMInference
        inference = HMMInference(make_test_params())
        
        # Path with long runs: R01 x 5, R02 x 5
        path = ["R01"] * 5 + ["R02"] * 5
        result = inference.enforce_dwell_time(path, min_dwell=3)
        self.assertEqual(result[:5], ["R01"] * 5)
        self.assertEqual(result[5:], ["R02"] * 5)

    def test_dwell_time_single_value_unchanged(self):
        """Verify single-value path is unchanged."""
        from investment_agent.regimes.hmm_inference import HMMInference
        inference = HMMInference(make_test_params())
        path = ["R01"]
        result = inference.enforce_dwell_time(path, min_dwell=3)
        self.assertEqual(result, ["R01"])


class TestPosteriorProbabilitiesSumToOne(unittest.TestCase):
    """Test that posterior probabilities always sum to 1.0."""

    def test_single_observation_probabilities_sum_to_one(self):
        """Verify probabilities sum to 1.0 for single observation."""
        detector = HMMRegimeDetector()
        features = [[50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5]]
        result = detector.classify(features)
        total = sum(result.probabilities.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_multiple_observation_probabilities_sum_to_one(self):
        """Verify probabilities sum to 1.0 for multiple observations."""
        detector = HMMRegimeDetector()
        features = [
            [50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5],
            [55.0, 0.5, 1.2, 22.0, 1.1, 0.6, 0.52],
            [60.0, 1.0, 1.5, 25.0, 1.3, 0.7, 0.55],
        ]
        result = detector.classify(features)
        total = sum(result.probabilities.values())
        self.assertAlmostEqual(total, 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
