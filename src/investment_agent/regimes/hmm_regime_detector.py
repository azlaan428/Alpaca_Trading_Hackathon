"""HMM Regime Detector — Authoritative Hidden Markov Model Regime Classification for X Quant X.

WHAT
====
Interface and baseline implementation for HMM-based market regime classification.
This module implements the authoritative architecture specified in:
    alpaca_paper_trading_specifications_x_quant_x/027_xquantx_regime_archetypes.txt

WHY
===
The rule-based detector (regime_detector.py) provides a deterministic approximation
for auditability and testing. The HMM detector is the authoritative implementation
that matches the papers' specification:

    market observations → HMM/regime probabilities → active regime

HOW
===
- Loads regime definitions from config/regimes.toml
- Computes emission probabilities from feature vector using multivariate Gaussian
- Applies Viterbi decoding or forward-backward smoothing for regime inference
- Enforces dwell-time constraints (MIN_REGIME_DWELL_BARS)
- Computes regime entropy H_t for uncertainty gating

The current implementation provides:
1. A clear interface contract (HMMRegimeDetector base class)
2. Configuration loading from config/regimes.toml
3. A stub implementation that raises NotImplementedError for the core inference
4. A factory function that returns the rule-based detector as fallback

IMPLEMENTATION STATUS
=====================
- Configuration loading: ✅ Implemented
- Interface contract: ✅ Implemented
- HMM inference (Baum-Welch, Viterbi): ❌ Stub (future enhancement)
- Dwell-time enforcement: ❌ Stub (future enhancement)
- Regime entropy computation: ❌ Stub (future enhancement)

The rule-based detector remains the active implementation until HMM inference
is fully implemented and tested.

Architectural Role
==================
Authoritative regime classification layer. Consumes market features and produces
HMM-based regime probabilities consumed by agent_reputation.py, ensemble_signal.py,
and capital_gate.py.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tomllib

from ..regimes.regimes import VALID_REGIMES


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _load_regime_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load regime definitions from config/regimes.toml.

    Parameters
    ----------
    path : Optional[Path]
        Custom path to regimes.toml. If None, uses default locations.

    Returns
    -------
    Dict[str, Any]
        Parsed regime configuration.
    """
    if path is None:
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "config" / "regimes.toml",
            Path.cwd() / "config" / "regimes.toml",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                path = candidate
                break

    if path is None or not path.exists():
        return {}

    try:
        with path.open("rb") as fp:
            return tomllib.load(fp)
    except Exception:
        return {}


_REGIME_CONFIG = _load_regime_config()


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeProbability:
    """Immutable HMM regime probability result.

    Attributes
    ----------
    regime : str
        Most probable regime identifier (R01-R12).
    probabilities : Dict[str, float]
        Probability distribution over all 12 regimes summing to 1.0.
        These ARE statistically calibrated HMM posterior probabilities.
    entropy : float
        Regime entropy H_t = -sum_k P(r_k|x_t) ln P(r_k|x_t).
    dwell_time : int
        Minimum dwell time in bars for the classified regime.
    is_confident : bool
        True if normalized entropy U_t = H_t / ln(12) < 0.5.
    timestamp : datetime
        Inference timestamp.
    """

    regime: str
    probabilities: Dict[str, float]
    entropy: float
    dwell_time: int
    is_confident: bool
    timestamp: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

class HMMRegimeDetector(ABC):
    """Abstract base class for HMM-based regime detectors.

    Subclasses must implement the core HMM inference methods.
    """

    @abstractmethod
    def classify(self, features: List[float]) -> RegimeProbability:
        """Classify regime from feature vector using HMM inference.

        Parameters
        ----------
        features : List[float]
            Feature vector [RSI, MACD, ATR, VIX, VolRatio, Corr, Hurst].

        Returns
        -------
        RegimeProbability
            HMM-based regime classification with calibrated probabilities.
        """
        pass

    @abstractmethod
    def update_transition_matrix(self, new_matrix: List[List[float]]) -> None:
        """Update the HMM transition matrix.

        Parameters
        ----------
        new_matrix : List[List[float]]
            12x12 transition matrix where each row sums to 1.0.
        """
        pass

    @abstractmethod
    def get_emission_parameters(self, regime: str) -> Dict[str, float]:
        """Get emission distribution parameters for a regime.

        Parameters
        ----------
        regime : str
            Regime identifier (R01-R12).

        Returns
        -------
        Dict[str, float]
            Emission distribution parameters (mean, covariance).
        """
        pass


# ---------------------------------------------------------------------------
# Stub implementation
# ---------------------------------------------------------------------------

class StubHMMRegimeDetector(HMMRegimeDetector):
    """Stub HMM regime detector.

    This implementation raises NotImplementedError for all core methods,
    clearly indicating that HMM inference is a future enhancement.

    Use get_hmm_detector() to obtain an instance; it returns this stub
    unless a full implementation is available.
    """

    def classify(self, features: List[float]) -> RegimeProbability:
        """Raise NotImplementedError — HMM inference not yet implemented."""
        raise NotImplementedError(
            "HMM regime inference is not yet implemented. "
            "Use regime_detector.RegimeDetector for the current rule-based approximation."
        )

    def update_transition_matrix(self, new_matrix: List[List[float]]) -> None:
        """Raise NotImplementedError — HMM transition matrix update not yet implemented."""
        raise NotImplementedError(
            "HMM transition matrix update is not yet implemented."
        )

    def get_emission_parameters(self, regime: str) -> Dict[str, float]:
        """Raise NotImplementedError — HMM emission parameters not yet implemented."""
        raise NotImplementedError(
            "HMM emission parameters are not yet implemented."
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_hmm_detector() -> HMMRegimeDetector:
    """Get the HMM regime detector.

    Currently returns the stub implementation. When HMM inference is implemented,
    this factory will return the production HMM detector.

    Returns
    -------
    HMMRegimeDetector
        HMM regime detector instance.
    """
    return StubHMMRegimeDetector()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "HMMRegimeDetector",
    "StubHMMRegimeDetector",
    "RegimeProbability",
    "get_hmm_detector",
    "_load_regime_config",
]
