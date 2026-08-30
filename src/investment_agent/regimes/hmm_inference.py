"""HMM Inference Engine — Forward-Backward, Viterbi, and Emission Model for X Quant X.

WHAT
====
Implements the core Hidden Markov Model inference algorithms for the 12-state
market regime classifier specified in:
    alpaca_paper_trading_specifications_x_quant_x/027_xquantx_regime_archetypes.txt

WHY
===
The authoritative X Quant X architecture requires HMM-based regime modeling with:
- 12 hidden states (R01-R12)
- 7-feature emission distributions (multivariate Gaussian)
- Transition matrix with persistence guarantees
- Dwell-time constraints
- Regime entropy for uncertainty gating

This module provides the mathematical primitives that make that operational.

HOW
===
- Forward-backward algorithm with scaling for posterior state probabilities
- Viterbi algorithm (log-space) for most probable regime sequence
- Multivariate Gaussian emissions with diagonal covariance
- Dwell-time enforcement (MIN_REGIME_DWELL_BARS = 3)
- Regime entropy H_t and normalized entropy U_t

Mathematical Specification
==========================
- Forward: alpha_t(i) = P(O_1..O_t, q_t=i | lambda)
- Backward: beta_t(i) = P(O_{t+1}..O_T | q_t=i, lambda)
- Posterior: gamma_t(i) = alpha_t(i) * beta_t(i) / P(O|lambda)
- Viterbi: delta_t(i) = max_{q_1..q_{t-1}} P(q_1..q_t=i, O_1..O_T | lambda)
- Emission: P(O_t | q_t=i, lambda) = N(O_t | mu_i, Sigma_i)
- Entropy: H_t = -sum_i gamma_t(i) * log(gamma_t(i))
- Normalized: U_t = H_t / ln(N)

Architectural Role
==================
Authoritative inference engine. Consumes market feature vectors and produces
statistically calibrated regime probabilities consumed by hmm_regime_detector.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np

from .regimes import VALID_REGIMES


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Number of hidden states (R01-R12)
N_STATES: int = 12

# Number of observation features
# [RSI, MACD, ATR(s), VIX, VolRatio, Corr, Hurst]
N_FEATURES: int = 7

# Minimum dwell time in bars before confirming regime transition
MIN_DWELL_BARS: int = 3

# Default emission covariance diagonal variance (tunable)
_DEFAULT_EMISSION_VARIANCE: float = 1.0

# Small constant to prevent log(0)
_EPSILON: float = 1e-300


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HMMParameters:
    """Immutable HMM parameter set.

    Attributes
    ----------
    transition_matrix : np.ndarray
        12x12 row-stochastic transition matrix A where A[i][j] = P(q_{t+1}=j | q_t=i).
    prior : np.ndarray
        12-element prior probability vector pi where pi[i] = P(q_1=i).
    emission_means : np.ndarray
        12x7 matrix of emission distribution means mu_i for each state.
    emission_covariances : np.ndarray
        12x7 diagonal covariance matrix (shared variance across features per state).
    """

    transition_matrix: np.ndarray
    prior: np.ndarray
    emission_means: np.ndarray
    emission_covariances: np.ndarray

    def __post_init__(self) -> None:
        """Validate HMM parameters."""
        # Validate transition matrix
        if self.transition_matrix.shape != (N_STATES, N_STATES):
            raise ValueError(
                f"transition_matrix must be {N_STATES}x{N_STATES}, got {self.transition_matrix.shape}"
            )
        row_sums = self.transition_matrix.sum(axis=1)
        if not np.allclose(row_sums, 1.0, atol=1e-9):
            raise ValueError(
                f"transition_matrix rows must sum to 1.0, got {row_sums}"
            )

        # Validate prior
        if self.prior.shape != (N_STATES,):
            raise ValueError(
                f"prior must be length {N_STATES}, got {self.prior.shape}"
            )
        prior_sum = self.prior.sum()
        if not math.isclose(prior_sum, 1.0, abs_tol=1e-9):
            raise ValueError(f"prior must sum to 1.0, got {prior_sum}")

        # Validate emission means
        if self.emission_means.shape != (N_STATES, N_FEATURES):
            raise ValueError(
                f"emission_means must be {N_STATES}x{N_FEATURES}, got {self.emission_means.shape}"
            )

        # Validate emission covariances
        if self.emission_covariances.shape != (N_STATES, N_FEATURES):
            raise ValueError(
                f"emission_covariances must be {N_STATES}x{N_FEATURES}, got {self.emission_covariances.shape}"
            )


@dataclass(frozen=True)
class HMMInferenceResult:
    """Immutable HMM inference result.

    Attributes
    ----------
    regime : str
        Most probable regime identifier (R01-R12) from Viterbi decoding.
    posterior_probabilities : np.ndarray
        12-element array of posterior state probabilities P(q_t=i | O, lambda).
        These ARE statistically calibrated HMM posterior probabilities.
    log_likelihood : float
        Log-likelihood of observation sequence: log P(O | lambda).
    viterbi_path : List[str]
        Most probable state sequence from Viterbi algorithm (after dwell-time enforcement).
    entropy : float
        Regime entropy H_t = -sum_i gamma_t(i) * log(gamma_t(i)).
    normalized_entropy : float
        Normalized entropy U_t = H_t / ln(N) in [0, 1].
    is_confident : bool
        True if normalized entropy U_t < 0.5 (per architecture spec).
    timestamp : datetime
        Inference timestamp.
    """

    regime: str
    posterior_probabilities: np.ndarray
    log_likelihood: float
    viterbi_path: List[str]
    entropy: float
    normalized_entropy: float
    is_confident: bool
    timestamp: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# HMM Inference Engine
# ---------------------------------------------------------------------------

class HMMInference:
    """Forward-backward and Viterbi inference engine for 12-state HMM.

    Uses scaled forward-backward algorithm for numerical stability.
    """

    def __init__(self, params: HMMParameters) -> None:
        """Initialize with HMM parameters.

        Parameters
        ----------
        params : HMMParameters
            Validated HMM parameter set.
        """
        self._params = params

    def forward_backward(
        self, observations: np.ndarray
    ) -> Tuple[np.ndarray, float, np.ndarray, np.ndarray]:
        """Run scaled forward-backward algorithm.

        Parameters
        ----------
        observations : np.ndarray
            T x 7 matrix of observation feature vectors.

        Returns
        -------
        gamma : np.ndarray
            T x 12 matrix of posterior state probabilities.
        log_likelihood : float
            Log-likelihood of observation sequence.
        alpha : np.ndarray
            T x 12 scaled forward variables.
        beta : np.ndarray
            T x 12 scaled backward variables.
        """
        T = observations.shape[0]
        N = N_STATES
        A = self._params.transition_matrix
        pi = self._params.prior
        means = self._params.emission_means
        covs = self._params.emission_covariances

        # Precompute emission probabilities
        B = np.zeros((T, N))
        for t in range(T):
            for i in range(N):
                B[t, i] = self._gaussian_pdf(observations[t], means[i], covs[i])

        # Scaled forward pass
        alpha = np.zeros((T, N))
        scale = np.zeros(T)

        # Initialize
        alpha[0, :] = pi * B[0, :]
        scale[0] = alpha[0, :].sum()
        if scale[0] < _EPSILON:
            scale[0] = _EPSILON
        alpha[0, :] /= scale[0]

        # Recursion
        for t in range(1, T):
            for j in range(N):
                alpha[t, j] = B[t, j] * sum(alpha[t - 1, i] * A[i, j] for i in range(N))
            scale[t] = alpha[t, :].sum()
            if scale[t] < _EPSILON:
                scale[t] = _EPSILON
            alpha[t, :] /= scale[t]

        # Scaled backward pass
        beta = np.zeros((T, N))
        beta[T - 1, :] = 1.0 / scale[T - 1]

        for t in range(T - 2, -1, -1):
            for i in range(N):
                beta[t, i] = sum(
                    A[i, j] * B[t + 1, j] * beta[t + 1, j] for j in range(N)
                ) / scale[t]

        # Compute posterior probabilities
        gamma = alpha * beta
        gamma_sum = gamma.sum(axis=1, keepdims=True)
        gamma_sum[gamma_sum < _EPSILON] = _EPSILON
        gamma /= gamma_sum

        # Log-likelihood
        log_likelihood = -np.sum(np.log(scale))

        return gamma, log_likelihood, alpha, beta

    def viterbi(self, observations: np.ndarray) -> List[str]:
        """Run Viterbi algorithm in log-space.

        Parameters
        ----------
        observations : np.ndarray
            T x 7 matrix of observation feature vectors.

        Returns
        -------
        List[str]
            Most probable state sequence (regime IDs R01-R12).
        """
        T = observations.shape[0]
        N = N_STATES
        A = self._params.transition_matrix
        pi = self._params.prior
        means = self._params.emission_means
        covs = self._params.emission_covariances

        # Precompute log emission probabilities
        log_B = np.zeros((T, N))
        for t in range(T):
            for i in range(N):
                log_B[t, i] = math.log(
                    max(self._gaussian_pdf(observations[t], means[i], covs[i]), _EPSILON)
                )

        # Log transition matrix
        log_A = np.log(A + _EPSILON)
        log_pi = np.log(pi + _EPSILON)

        # Viterbi forward pass
        delta = np.zeros((T, N))
        psi = np.zeros((T, N), dtype=int)

        delta[0, :] = log_pi + log_B[0, :]

        for t in range(1, T):
            for j in range(N):
                scores = delta[t - 1, :] + log_A[:, j]
                psi[t, j] = np.argmax(scores)
                delta[t, j] = scores[psi[t, j]] + log_B[t, j]

        # Backtrack
        path = [0] * T
        path[T - 1] = np.argmax(delta[T - 1, :])

        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1, path[t + 1]]

        return [f"R{path[t] + 1:02d}" for t in range(T)]

    def enforce_dwell_time(self, path: List[str], min_dwell: int = MIN_DWELL_BARS) -> List[str]:
        """Enforce minimum dwell time on regime sequence.

        A regime transition is only confirmed if the new regime has been the
        most probable for >= min_dwell consecutive steps.

        Parameters
        ----------
        path : List[str]
            Raw Viterbi path.
        min_dwell : int
            Minimum dwell time in bars (default 3).

        Returns
        -------
        List[str]
            Path with dwell-time constraints enforced.
        """
        if len(path) <= min_dwell:
            return path

        result = list(path)
        i = 1
        while i < len(result):
            if result[i] != result[i - 1]:
                # Potential transition - check if it persists
                new_regime = result[i]
                j = i
                while j < len(result) and result[j] == new_regime:
                    j += 1
                run_length = j - i
                if run_length < min_dwell:
                    # Fill in with previous regime
                    for k in range(i, j):
                        result[k] = result[i - 1]
                    i = j
                else:
                    i = j
            else:
                i += 1

        return result

    def compute_entropy(self, posterior: np.ndarray) -> Tuple[float, float, bool]:
        """Compute regime entropy from posterior probabilities.

        Parameters
        ----------
        posterior : np.ndarray
            T x 12 matrix of posterior probabilities (use single time step).

        Returns
        -------
        entropy : float
            Shannon entropy H_t = -sum_i p_i * log(p_i).
        normalized_entropy : float
            Normalized entropy U_t = H_t / ln(N) in [0, 1].
        is_confident : bool
            True if U_t < 0.5 (per architecture spec).
        """
        # Use last time step
        p = posterior[-1, :].copy()
        p[p < _EPSILON] = _EPSILON
        p /= p.sum()

        entropy = -np.sum(p * np.log(p))
        normalized_entropy = entropy / math.log(N_STATES)
        is_confident = normalized_entropy < 0.5

        return float(entropy), float(normalized_entropy), bool(is_confident)

    def _gaussian_pdf(self, x: np.ndarray, mean: np.ndarray, cov_diag: np.ndarray) -> float:
        """Compute multivariate Gaussian PDF with diagonal covariance.

        Parameters
        ----------
        x : np.ndarray
            Observation vector (7 features).
        mean : np.ndarray
            Mean vector (7 features).
        cov_diag : np.ndarray
            Diagonal covariance vector (7 variances).

        Returns
        -------
        float
            Probability density.
        """
        diff = x - mean
        var = cov_diag + _EPSILON  # prevent division by zero
        exponent = -0.5 * np.sum(diff ** 2 / var)
        normalization = (2 * math.pi) ** (N_FEATURES / 2) * np.prod(np.sqrt(var))
        return math.exp(exponent) / normalization


# ---------------------------------------------------------------------------
# HMM Parameter Factory
# ---------------------------------------------------------------------------

def load_hmm_parameters(config: dict) -> HMMParameters:
    """Load HMM parameters from configuration dictionary.

    Parameters
    ----------
    config : dict
        Configuration from config/regimes.toml.

    Returns
    -------
    HMMParameters
        Validated HMM parameter set.
    """
    regimes = config.get("regimes", {})
    priors = config.get("priors", {})
    diag = config.get("transition_diagonal", {})
    emissions = config.get("emission_mean", {})

    # Build prior vector
    prior = np.zeros(N_STATES)
    for i in range(N_STATES):
        regime_id = f"R{i + 1:02d}"
        prior[i] = priors.get(regime_id, 1.0 / N_STATES)
    prior /= prior.sum()

    # Build transition matrix
    # Diagonal from config, off-diagonal distributed proportionally
    A = np.zeros((N_STATES, N_STATES))
    for i in range(N_STATES):
        regime_id = f"R{i + 1:02d}"
        p_ii = diag.get(regime_id, 0.85)
        # Clamp diagonal
        p_ii = max(0.0, min(1.0, p_ii))
        off_diag = (1.0 - p_ii) / (N_STATES - 1)
        A[i, :] = off_diag
        A[i, i] = p_ii

    # Build emission means
    means = np.zeros((N_STATES, N_FEATURES))
    feature_names = ["RSI", "MACD", "ATR", "VIX", "VolRatio", "Corr", "Hurst"]
    for i in range(N_STATES):
        regime_id = f"R{i + 1:02d}"
        emission = emissions.get(regime_id, {})
        for j, feat in enumerate(feature_names):
            means[i, j] = emission.get(feat, 0.0)

    # Build emission covariances (shared diagonal variance per state)
    covs = np.ones((N_STATES, N_FEATURES)) * _DEFAULT_EMISSION_VARIANCE

    return HMMParameters(
        transition_matrix=A,
        prior=prior,
        emission_means=means,
        emission_covariances=covs,
    )


# ---------------------------------------------------------------------------
# HMM Regime Detector (Concrete Implementation)
# ---------------------------------------------------------------------------

class HMMRegimeDetectorImpl:
    """Concrete HMM-based regime detector.

    Uses forward-backward inference for posterior probabilities and
    Viterbi decoding with dwell-time enforcement for regime classification.
    """

    def __init__(self, params: Optional[HMMParameters] = None) -> None:
        """Initialize HMM regime detector.

        Parameters
        ----------
        params : Optional[HMMParameters]
            HMM parameters. If None, loads from config/regimes.toml.
        """
        if params is None:
            from .hmm_regime_detector import _load_regime_config
            config = _load_regime_config()
            if not config:
                raise ValueError(
                    "Could not load regime configuration from config/regimes.toml"
                )
            params = load_hmm_parameters(config)

        self._params = params
        self._inference = HMMInference(params)
        self._history: List[HMMInferenceResult] = []

    def classify(self, features: np.ndarray) -> HMMInferenceResult:
        """Classify regime from feature sequence using HMM inference.

        Parameters
        ----------
        features : np.ndarray
            T x 7 matrix of observation feature vectors.
            Each row is [RSI, MACD, ATR, VIX, VolRatio, Corr, Hurst].

        Returns
        -------
        HMMInferenceResult
            HMM-based regime classification with calibrated probabilities.
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)

        T = features.shape[0]
        if T < 1:
            raise ValueError(f"Need at least 1 observation, got {T}")
        if features.shape[1] != N_FEATURES:
            raise ValueError(
                f"Expected {N_FEATURES} features per observation, got {features.shape[1]}"
            )

        # Run forward-backward
        gamma, log_likelihood, _, _ = self._inference.forward_backward(features)

        # Run Viterbi
        viterbi_path = self._inference.viterbi(features)

        # Enforce dwell time
        viterbi_path = self._inference.enforce_dwell_time(viterbi_path)

        # Compute entropy from last time step
        entropy, normalized_entropy, is_confident = self._inference.compute_entropy(gamma)

        # Most probable regime at last time step
        last_posterior = gamma[-1, :]
        most_probable_idx = int(np.argmax(last_posterior))
        regime = f"R{most_probable_idx + 1:02d}"

        result = HMMInferenceResult(
            regime=regime,
            posterior_probabilities=last_posterior.copy(),
            log_likelihood=log_likelihood,
            viterbi_path=viterbi_path,
            entropy=entropy,
            normalized_entropy=normalized_entropy,
            is_confident=is_confident,
        )

        self._history.append(result)
        return result

    def get_history(self) -> List[HMMInferenceResult]:
        """Return inference history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear inference history."""
        self._history.clear()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "HMMParameters",
    "HMMInferenceResult",
    "HMMInference",
    "HMMRegimeDetectorImpl",
    "load_hmm_parameters",
    "N_STATES",
    "N_FEATURES",
    "MIN_DWELL_BARS",
]
