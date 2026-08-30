"""Regime Detector — Market Regime Classification Layer for X Quant X.

WHAT
====
Classifies the current market environment into one of 12 canonical regimes (R01-R12)
based on price trend, volatility, and volume features extracted from historical market data.

WHY
===
Market regimes represent distinct macroeconomic and microstructural operating environments
(e.g., bull quiet, bear volatile, crisis deleveraging). Risk rules, agent reputation weights,
and allocation parameters vary by regime. The regime detector provides the current regime
classification and confidence to downstream modules.

HOW
===
- Extracts features from price/volume history: trend direction, volatility regime, volume regime
- Maps features to 12 canonical regimes using a deterministic rule-based classifier
- Tracks regime history and computes regime affinity scores (NOT statistically calibrated probabilities)
- Does NOT use ML/HMM (rule-based for auditability and testability)

Note: The authoritative X Quant X architecture specifies HMM-based regime modeling.
This module implements the deterministic feature-based classifier for auditability,
deterministic testability, and immediate operational use. HMM integration is a separate
future enhancement.

The 12 regimes are organized as:
    Trend × Volatility × Volume
    - Trend: Bullish (3), Neutral (3), Bearish (3)
    - Volatility: Normal, Elevated
    - Volume: Normal, Elevated

    This produces exactly 3 × 2 × 2 = 12 regimes: R01-R12.

Architectural Role
==================
Analytical classification layer. Consumes market data (prices, volumes) and produces
regime classifications consumed by agent_reputation.py, capital_gate.py, and
ensemble_signal.py. Performs no order placement or execution side-effects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from investment_agent.regimes.regimes import VALID_REGIMES


# ---------------------------------------------------------------------------
# Feature extraction thresholds
# ---------------------------------------------------------------------------

# Trend thresholds (annualized return)
_TREND_STRONG_BULL: float = 0.20   # >=20% annualized return
_TREND_WEAK_BULL: float = 0.05     # >=5% annualized return
_TREND_WEAK_BEAR: float = -0.05    # <=-5% annualized return
_TREND_STRONG_BEAR: float = -0.20  # <=-20% annualized return

# Volatility thresholds (annualized std dev)
_VOL_NORMAL_MAX: float = 0.15      # <=15% annualized vol = normal
_VOL_ELEVATED_MAX: float = 0.30    # <=30% annualized vol = elevated, >30% = crisis

# Volume thresholds (relative to moving average)
_VOL_RATIO_ELEVATED_MIN: float = 1.5  # >=1.5x average = elevated volume

# Lookback window for feature extraction (trading days)
_DEFAULT_LOOKBACK_DAYS: int = 20

# Minimum volume history required for reliable volume-ratio computation
_MIN_VOLUME_HISTORY_DAYS: int = 40  # 2x lookback for baseline comparison


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeClassification:
    """Immutable regime classification result.

    Attributes
    ----------
    regime : str
        Current regime identifier (one of R01-R12 from VALID_REGIMES).
    confidence : float
        Classification confidence in [0.0, 1.0]. This is a heuristic measure of
        feature clarity, NOT a statistical probability of correctness.
    timestamp : datetime
        Classification timestamp.
    features : Dict[str, float]
        Extracted market features used for classification.
    regime_affinity : Dict[str, float]
        Heuristic similarity scores over all 12 regimes summing to 1.0.
        These are NOT statistically calibrated probabilities. They represent
        a deterministic distance-based heuristic for regime similarity only.
    """

    regime: str
    confidence: float
    timestamp: datetime
    features: Dict[str, float]
    regime_affinity: Dict[str, float]

    @property
    def transition_probs(self) -> Dict[str, float]:
        """Backward-compatible accessor returning regime_affinity.

        .. deprecated::
            Use ``regime_affinity`` instead. These are NOT transition probabilities.
        """
        return self.regime_affinity


@dataclass(frozen=True)
class MarketFeatures:
    """Extracted market features for regime classification.

    Attributes
    ----------
    returns : List[float]
        Daily returns series.
    annualized_return : float
        Annualized mean return.
    annualized_volatility : float
        Annualized standard deviation of returns.
    volume_ratio : float
        Recent average volume / long-term average volume. NaN if insufficient history.
    trend_strength : float
        Absolute trend strength (|annualized_return|).
    volatility_regime : str
        "normal", "elevated", or "crisis".
    volume_regime : str
        "normal", "elevated", or "unavailable" (when insufficient volume history).
    """

    returns: List[float]
    annualized_return: float
    annualized_volatility: float
    volume_ratio: float
    trend_strength: float
    volatility_regime: str
    volume_regime: str


# ---------------------------------------------------------------------------
# Regime mapping
# ---------------------------------------------------------------------------

# 12-regime mapping: (trend_category, volatility_regime, volume_regime) -> regime_id
# Trend: bullish/neutral/bearish (3)
# Volatility: normal/elevated (2)
# Volume: normal/elevated (2)
# Total: 3 x 2 x 2 = 12 regimes
_REGIME_MAP: Dict[Tuple[str, str, str], str] = {
    # Bullish trend
    ("bullish", "normal", "normal"): "R01",
    ("bullish", "normal", "elevated"): "R02",
    ("bullish", "elevated", "normal"): "R03",
    ("bullish", "elevated", "elevated"): "R04",
    # Neutral trend
    ("neutral", "normal", "normal"): "R05",
    ("neutral", "normal", "elevated"): "R06",
    ("neutral", "elevated", "normal"): "R07",
    ("neutral", "elevated", "elevated"): "R08",
    # Bearish trend
    ("bearish", "normal", "normal"): "R09",
    ("bearish", "normal", "elevated"): "R10",
    ("bearish", "elevated", "normal"): "R11",
    ("bearish", "elevated", "elevated"): "R12",
}

# Reverse mapping: regime_id -> (trend_category, volatility_regime, volume_regime)
_REVERSE_REGIME_MAP: Dict[str, Tuple[str, str, str]] = {v: k for k, v in _REGIME_MAP.items()}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_prices(prices: List[float]) -> None:
    """Validate price series for NaN, Inf, non-positive, and empty input."""
    if not prices:
        raise ValueError("Price series must be non-empty")
    if len(prices) < 2:
        raise ValueError(f"Price series must contain at least 2 values, got {len(prices)}")

    for i, price in enumerate(prices):
        if math.isnan(price):
            raise ValueError(f"Price at index {i} is NaN")
        if math.isinf(price):
            raise ValueError(f"Price at index {i} is Infinity")
        if price <= 0.0:
            raise ValueError(f"Price at index {i} is non-positive: {price}")


def _validate_volumes(volumes: Optional[List[float]]) -> None:
    """Validate volume series for NaN, Inf, negative values."""
    if volumes is None:
        return
    if not volumes:
        raise ValueError("Volume series must be non-empty if provided")

    for i, volume in enumerate(volumes):
        if math.isnan(volume):
            raise ValueError(f"Volume at index {i} is NaN")
        if math.isinf(volume):
            raise ValueError(f"Volume at index {i} is Infinity")
        if volume < 0.0:
            raise ValueError(f"Volume at index {i} is negative: {volume}")


def _validate_lengths(prices: List[float], volumes: Optional[List[float]]) -> None:
    """Validate that price and volume series have compatible lengths."""
    if volumes is not None and len(volumes) < len(prices):
        raise ValueError(
            f"Volume series shorter than price series: {len(prices)} prices, "
            f"{len(volumes)} volumes. Volumes must be at least as long as prices."
        )


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def _extract_features(
    prices: List[float],
    volumes: Optional[List[float]] = None,
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS,
) -> MarketFeatures:
    """Extract market features from price and volume history.

    Parameters
    ----------
    prices : List[float]
        Historical price series (oldest first). Must contain at least 2 finite,
        positive values.
    volumes : Optional[List[float]]
        Historical volume series (oldest first). If None or insufficient length,
        volume features are marked as unavailable.
    lookback_days : int
        Lookback window for feature calculation.

    Returns
    -------
    MarketFeatures
        Extracted market features.

    Raises
    ------
    ValueError
        If inputs contain NaN, Inf, negative prices, zero prices, mismatched lengths,
        or insufficient data points.
    """
    _validate_prices(prices)
    _validate_volumes(volumes)
    _validate_lengths(prices, volumes)

    # Use recent window
    recent_prices = prices[-lookback_days:] if len(prices) >= lookback_days else prices
    n = len(recent_prices)

    # Compute returns
    returns = []
    for i in range(1, n):
        ret = (recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1]
        returns.append(ret)

    if not returns:
        returns = [0.0]

    # Annualized statistics (assuming daily data, 252 trading days/year)
    annualization_factor = math.sqrt(252.0)
    mean_return = sum(returns) / len(returns)
    annualized_return = mean_return * 252.0

    if len(returns) > 1:
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0
    annualized_volatility = std_dev * annualization_factor

    # Volume ratio: require sufficient history for meaningful comparison
    volume_ratio = float('nan')
    volume_regime = "unavailable"

    if volumes is not None and len(volumes) >= _MIN_VOLUME_HISTORY_DAYS:
        recent_volumes = volumes[-lookback_days:]
        long_term_volumes = volumes[-2 * lookback_days : -lookback_days]
        long_term_avg = sum(long_term_volumes) / len(long_term_volumes)
        if long_term_avg > 0.0:
            recent_avg = sum(recent_volumes) / len(recent_volumes)
            volume_ratio = recent_avg / long_term_avg
            volume_regime = "elevated" if volume_ratio >= _VOL_RATIO_ELEVATED_MIN else "normal"
    elif volumes is not None and len(volumes) >= lookback_days:
        # Insufficient history for baseline comparison; mark as unavailable
        volume_regime = "unavailable"
        volume_ratio = float('nan')

    # Classify trend
    if annualized_return >= _TREND_STRONG_BULL:
        trend_category = "bullish"
    elif annualized_return >= _TREND_WEAK_BULL:
        trend_category = "bullish"
    elif annualized_return <= _TREND_STRONG_BEAR:
        trend_category = "bearish"
    elif annualized_return <= _TREND_WEAK_BEAR:
        trend_category = "bearish"
    else:
        trend_category = "neutral"

    # Classify volatility
    if annualized_volatility > _VOL_ELEVATED_MAX:
        volatility_regime = "crisis"
    elif annualized_volatility > _VOL_NORMAL_MAX:
        volatility_regime = "elevated"
    else:
        volatility_regime = "normal"

    # Clamp crisis volatility to elevated for regime mapping
    if volatility_regime == "crisis":
        volatility_regime = "elevated"

    trend_strength = abs(annualized_return)

    return MarketFeatures(
        returns=returns,
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        volume_ratio=volume_ratio,
        trend_strength=trend_strength,
        volatility_regime=volatility_regime,
        volume_regime=volume_regime,
    )


# ---------------------------------------------------------------------------
# Regime classification
# ---------------------------------------------------------------------------

def _compute_confidence(features: MarketFeatures) -> float:
    """Compute classification confidence based on feature clarity.

    Higher confidence when:
    - Trend is strong (far from zero)
    - Volatility is clearly in one regime
    - Volume is clearly normal or elevated (if available)

    Note: This is a heuristic measure of feature clarity, NOT a statistical
    probability of classification correctness.
    """
    # Trend clarity: 0.0 at neutral, 1.0 at strong trend
    trend_clarity = min(1.0, features.trend_strength / 0.20)

    # Volatility clarity: 0.0 at boundary, 1.0 deep in a regime
    vol_mid = (_VOL_NORMAL_MAX + _VOL_ELEVATED_MAX) / 2.0
    if features.annualized_volatility < _VOL_NORMAL_MAX:
        vol_clarity = 1.0 - (_VOL_NORMAL_MAX - features.annualized_volatility) / _VOL_NORMAL_MAX
    elif features.annualized_volatility < _VOL_ELEVATED_MAX:
        vol_clarity = 1.0 - abs(features.annualized_volatility - vol_mid) / (vol_mid - _VOL_NORMAL_MAX)
    else:
        vol_clarity = min(1.0, (features.annualized_volatility - _VOL_ELEVATED_MAX) / _VOL_ELEVATED_MAX)

    vol_clarity = max(0.0, min(1.0, vol_clarity))

    # Volume clarity: 0.0 at boundary or unavailable, 1.0 deep in a regime
    if features.volume_regime == "unavailable" or math.isnan(features.volume_ratio):
        volume_clarity = 0.0
    else:
        vol_ratio_mid = 1.5  # boundary between normal and elevated
        if features.volume_ratio < 1.5:
            volume_clarity = 1.0 - (1.5 - features.volume_ratio) / 1.5
        else:
            volume_clarity = min(1.0, (features.volume_ratio - 1.5) / 1.5)

        volume_clarity = max(0.0, min(1.0, volume_clarity))

    # Combined confidence: trend and volatility weighted more when volume unavailable
    if features.volume_regime == "unavailable" or math.isnan(features.volume_ratio):
        confidence = (trend_clarity + vol_clarity) / 2.0
    else:
        confidence = (trend_clarity + vol_clarity + volume_clarity) / 3.0

    return max(0.0, min(1.0, confidence))


def _compute_transition_probabilities(
    regime: str,
    confidence: float,
    features: MarketFeatures,
) -> Dict[str, float]:
    """Backward-compatible alias for _compute_regime_affinity.

    Returns heuristic regime affinity scores over all 12 regimes summing to 1.0.
    These are NOT statistically calibrated probabilities. They represent
    a deterministic distance-based heuristic for regime similarity only.
    """
    return _compute_regime_affinity(regime, confidence, features)


def _compute_regime_affinity(
    regime: str,
    confidence: float,
    features: MarketFeatures,
) -> Dict[str, float]:
    """Compute heuristic regime affinity scores over all 12 regimes.

    Uses a simple distance-based model: regimes closer to the classified one
    receive higher affinity scores proportional to classification confidence.

    IMPORTANT: These are NOT statistically calibrated probabilities. They are
    deterministic heuristic similarity scores based on feature-space distance.
    Do NOT interpret them as transition probabilities or likelihoods.

    Parameters
    ----------
    regime : str
        Current classified regime.
    confidence : float
        Classification confidence in [0.0, 1.0]. Higher confidence concentrates
        affinity on the classified regime; lower confidence spreads affinity
        more uniformly.
    features : MarketFeatures
        Extracted market features.

    Returns
    -------
    Dict[str, float]
        Heuristic affinity scores over all 12 regimes summing to 1.0.
    """
    probs: Dict[str, float] = {}

    # Get current regime characteristics
    current_key = _REVERSE_REGIME_MAP.get(regime)
    if current_key is None:
        # Fallback: uniform distribution
        uniform = 1.0 / len(VALID_REGIMES)
        return {r: uniform for r in sorted(VALID_REGIMES)}

    current_trend, current_vol, current_vol_ratio = current_key

    # Compute distances to all regimes
    total_weight = 0.0
    for r in sorted(VALID_REGIMES):
        key = _REVERSE_REGIME_MAP.get(r)
        if key is None:
            continue

        trend, vol, vol_ratio = key

        # Distance: 0 if same trend, 2 if opposite trend (bullish vs bearish), 1 if neutral
        if trend == current_trend:
            trend_dist = 0.0
        elif trend == "neutral" or current_trend == "neutral":
            trend_dist = 1.0
        else:
            trend_dist = 2.0

        vol_dist = 0.0 if vol == current_vol else 1.0
        vol_ratio_dist = 0.0 if vol_ratio == current_vol_ratio else 1.0

        distance = trend_dist + vol_dist + vol_ratio_dist

        # Weight: higher for closer regimes, modulated by confidence
        # At confidence=1.0, only the exact regime gets weight
        # At confidence=0.0, all regimes get equal weight
        weight = math.exp(-distance * (1.0 - confidence + 0.1))
        probs[r] = weight
        total_weight += weight

    # Normalize
    if total_weight > 0.0:
        for r in probs:
            probs[r] /= total_weight
    else:
        uniform = 1.0 / len(VALID_REGIMES)
        probs = {r: uniform for r in sorted(VALID_REGIMES)}

    return probs


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

class RegimeDetector:
    """Market regime classifier for the X Quant X architecture.

    WHAT
    ====
    Classifies the current market environment into one of 12 canonical regimes (R01-R12)
    based on price trend, volatility, and volume features.

    WHY
    ====
    Market regimes drive parameter selection in agent reputation tracking, capital gating,
    and ensemble signal aggregation. Accurate regime classification ensures the system
    uses the right risk parameters for current market conditions.

    HOW
    ====
    1. Validate input data for numerical correctness.
    2. Accept price and optional volume history.
    3. Extract features: annualized return, annualized volatility, volume ratio.
    4. Classify trend (bullish/neutral/bearish), volatility (normal/elevated), volume (normal/elevated/unavailable).
    5. Map feature combination to regime ID via lookup table.
    6. Compute confidence (heuristic) and regime affinity scores.

    Parameters
    ----------
    lookback_days : int, optional
        Lookback window for feature extraction (default 20 trading days).

    Raises
    ------
    ValueError
        If lookback_days is negative or zero.
    """

    def __init__(self, lookback_days: int = _DEFAULT_LOOKBACK_DAYS) -> None:
        if not isinstance(lookback_days, int) or lookback_days <= 0:
            raise ValueError(f"lookback_days must be a positive integer, got {lookback_days}")

        self._lookback_days = lookback_days
        self._history: List[Tuple[datetime, str, float]] = []  # (timestamp, regime, confidence)

    def classify(
        self,
        prices: List[float],
        volumes: Optional[List[float]] = None,
        timestamp: Optional[datetime] = None,
    ) -> RegimeClassification:
        """Classify current market regime from price and volume history.

        Parameters
        ----------
        prices : List[float]
            Historical price series (oldest first). Must contain at least 2
            finite, positive values.
        volumes : Optional[List[float]]
            Historical volume series (oldest first). If None or shorter than
            2x lookback_days, volume features are marked as unavailable.
        timestamp : Optional[datetime]
            Classification timestamp. Defaults to datetime.now().

        Returns
        -------
        RegimeClassification
            Classification result with regime ID, confidence, features, and regime affinity.

        Raises
        ------
        ValueError
            If inputs contain NaN, Inf, negative prices, zero prices, mismatched lengths,
            or insufficient data points.
        """
        if timestamp is None:
            timestamp = datetime.now()

        features = _extract_features(prices, volumes, self._lookback_days)

        # Map features to regime
        if features.annualized_return >= _TREND_STRONG_BULL:
            trend_category = "bullish"
        elif features.annualized_return >= _TREND_WEAK_BULL:
            trend_category = "bullish"
        elif features.annualized_return <= _TREND_STRONG_BEAR:
            trend_category = "bearish"
        elif features.annualized_return <= _TREND_WEAK_BEAR:
            trend_category = "bearish"
        else:
            trend_category = "neutral"

        # Use "normal" volume regime when unavailable for mapping purposes
        volume_regime_for_mapping = features.volume_regime if features.volume_regime != "unavailable" else "normal"

        regime = _REGIME_MAP.get(
            (trend_category, features.volatility_regime, volume_regime_for_mapping),
            "R05",  # Default to neutral-normal-normal
        )

        # Explicit validation: output regime must be in VALID_REGIMES
        if regime not in VALID_REGIMES:
            raise ValueError(
                f"Classified regime '{regime}' is not in VALID_REGIMES. "
                f"This indicates a bug in the regime mapping table."
            )

        confidence = _compute_confidence(features)
        regime_affinity = _compute_regime_affinity(regime, confidence, features)

        # Record history
        self._history.append((timestamp, regime, confidence))

        return RegimeClassification(
            regime=regime,
            confidence=confidence,
            timestamp=timestamp,
            features={
                "annualized_return": features.annualized_return,
                "annualized_volatility": features.annualized_volatility,
                "volume_ratio": features.volume_ratio,
                "trend_strength": features.trend_strength,
                "trend_category": trend_category,
                "volatility_regime": features.volatility_regime,
                "volume_regime": features.volume_regime,
            },
            regime_affinity=regime_affinity,
        )

    def get_history(self, lookback_days: Optional[int] = None) -> List[Tuple[datetime, str, float]]:
        """Return regime classification history.

        Parameters
        ----------
        lookback_days : Optional[int]
            If provided, return only entries within this many days.

        Returns
        -------
        List[Tuple[datetime, str, float]]
            List of (timestamp, regime, confidence) tuples.
        """
        if lookback_days is None:
            return list(self._history)

        cutoff = datetime.now() - timedelta(days=lookback_days)
        return [(ts, r, c) for ts, r, c in self._history if ts > cutoff]

    def clear_history(self) -> None:
        """Clear regime classification history."""
        self._history.clear()


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def detect_regime(
    prices: List[float],
    volumes: Optional[List[float]] = None,
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS,
    timestamp: Optional[datetime] = None,
) -> RegimeClassification:
    """Convenience function to classify market regime without instantiating RegimeDetector.

    Parameters
    ----------
    prices : List[float]
        Historical price series (oldest first). Must contain at least 2
        finite, positive values.
    volumes : Optional[List[float]]
        Historical volume series (oldest first).
    lookback_days : int, optional
        Lookback window for feature extraction (default 20).
    timestamp : Optional[datetime]
        Classification timestamp. Defaults to datetime.now().

    Returns
    -------
    RegimeClassification
        Classification result.
    """
    detector = RegimeDetector(lookback_days=lookback_days)
    return detector.classify(prices, volumes, timestamp)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "RegimeClassification",
    "MarketFeatures",
    "RegimeDetector",
    "detect_regime",
    "_compute_transition_probabilities",
]
