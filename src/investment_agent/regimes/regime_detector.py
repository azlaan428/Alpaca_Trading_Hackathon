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
- Tracks regime history and computes transition probabilities
- Does NOT use ML/HMM (rule-based for auditability and testability)

The 12 regimes are organized as:
    Trend × Volatility × Volume
    - Trend: Bullish (3), Neutral (3), Bearish (3), Sideways (3)
    - Volatility: Normal, Elevated
    - Volume: Normal, Elevated

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
_TREND_STRONG_BULL: float = 0.20   # >20% annualized return
_TREND_WEAK_BULL: float = 0.05     # >5% annualized return
_TREND_WEAK_BEAR: float = -0.05    # <-5% annualized return
_TREND_STRONG_BEAR: float = -0.20  # <-20% annualized return

# Volatility thresholds (annualized std dev)
_VOL_NORMAL_MAX: float = 0.15      # <15% annualized vol = normal
_VOL_ELEVATED_MAX: float = 0.30    # <30% annualized vol = elevated, >30% = crisis

# Volume thresholds (relative to moving average)
_VOL_RATIO_NORMAL_MAX: float = 1.5       # <1.5x average = normal volume
_VOL_RATIO_ELEVATED_MIN: float = 1.5     # >=1.5x average = elevated volume

# Lookback window for feature extraction (trading days)
_DEFAULT_LOOKBACK_DAYS: int = 20


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegimeClassification:
    """Immutable regime classification result.

    Attributes
    ----------
    regime : str
        Current regime identifier (one of R01-R12).
    confidence : float
        Classification confidence in [0.0, 1.0].
    timestamp : datetime
        Classification timestamp.
    features : Dict[str, float]
        Extracted market features used for classification.
    transition_probs : Dict[str, float]
        Probability distribution over all 12 regimes.
    """

    regime: str
    confidence: float
    timestamp: datetime
    features: Dict[str, float]
    transition_probs: Dict[str, float]


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
        Recent average volume / long-term average volume.
    trend_strength : float
        Absolute trend strength (|annualized_return|).
    volatility_regime : str
        "normal", "elevated", or "crisis".
    volume_regime : str
        "normal" or "elevated".
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
        Historical price series (oldest first).
    volumes : Optional[List[float]]
        Historical volume series (oldest first). If None, volume features are set to defaults.
    lookback_days : int
        Lookback window for feature calculation.

    Returns
    -------
    MarketFeatures
        Extracted market features.
    """
    if len(prices) < 2:
        raise ValueError(f"Insufficient price data: need at least 2 prices, got {len(prices)}")

    # Use recent window
    recent_prices = prices[-lookback_days:] if len(prices) >= lookback_days else prices
    n = len(recent_prices)

    # Compute returns
    returns = []
    for i in range(1, n):
        if recent_prices[i - 1] != 0.0:
            ret = (recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1]
            returns.append(ret)
        else:
            returns.append(0.0)

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

    # Volume ratio
    volume_ratio = 1.0
    if volumes and len(volumes) >= lookback_days:
        recent_volumes = volumes[-lookback_days:]
        if len(volumes) >= 2 * lookback_days:
            long_term_volumes = volumes[-2 * lookback_days : -lookback_days]
            long_term_avg = sum(long_term_volumes) / len(long_term_volumes)
            if long_term_avg > 0.0:
                recent_avg = sum(recent_volumes) / len(recent_volumes)
                volume_ratio = recent_avg / long_term_avg
        else:
            recent_avg = sum(recent_volumes) / len(recent_volumes)
            volume_ratio = recent_avg / max(recent_avg, 1.0)

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

    # Classify volume
    volume_regime = "elevated" if volume_ratio >= _VOL_RATIO_ELEVATED_MIN else "normal"

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
    - Volume is clearly normal or elevated
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

    # Volume clarity: 0.0 at boundary, 1.0 deep in a regime
    vol_ratio_mid = (_VOL_RATIO_NORMAL_MAX + _VOL_RATIO_ELEVATED_MIN) / 2.0
    if features.volume_ratio < _VOL_RATIO_NORMAL_MAX:
        volume_clarity = 1.0 - (_VOL_RATIO_NORMAL_MAX - features.volume_ratio) / _VOL_RATIO_NORMAL_MAX
    elif features.volume_ratio < _VOL_RATIO_ELEVATED_MIN:
        volume_clarity = 1.0 - abs(features.volume_ratio - vol_ratio_mid) / (vol_ratio_mid - _VOL_RATIO_NORMAL_MAX)
    else:
        volume_clarity = min(1.0, (features.volume_ratio - _VOL_RATIO_ELEVATED_MIN) / _VOL_RATIO_ELEVATED_MIN)

    volume_clarity = max(0.0, min(1.0, volume_clarity))

    # Combined confidence
    confidence = (trend_clarity + vol_clarity + volume_clarity) / 3.0
    return max(0.0, min(1.0, confidence))


def _compute_transition_probabilities(
    regime: str,
    confidence: float,
    features: MarketFeatures,
) -> Dict[str, float]:
    """Compute transition probabilities over all 12 regimes.

    Uses a simple distance-based model: regimes closer to the classified one
    receive higher probability mass proportional to confidence.

    Parameters
    ----------
    regime : str
        Current classified regime.
    confidence : float
        Classification confidence in [0.0, 1.0].
    features : MarketFeatures
        Extracted market features.

    Returns
    -------
    Dict[str, float]
        Probability distribution over all 12 regimes summing to 1.0.
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

        # Distance: 0 if same trend, 1 if adjacent, 2 if opposite
        trend_dist = 0.0 if trend == current_trend else 2.0
        vol_dist = 0.0 if vol == current_vol else 1.0
        vol_ratio_dist = 0.0 if vol_ratio == current_vol_ratio else 1.0

        distance = trend_dist + vol_dist + vol_ratio_dist

        # Weight: higher for closer regimes, modulated by confidence
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
    1. Accept price and optional volume history.
    2. Extract features: annualized return, annualized volatility, volume ratio.
    3. Classify trend (bullish/neutral/bearish), volatility (normal/elevated), volume (normal/elevated).
    4. Map feature combination to regime ID via lookup table.
    5. Compute confidence and transition probabilities.

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
            Historical price series (oldest first).
        volumes : Optional[List[float]]
            Historical volume series (oldest first).
        timestamp : Optional[datetime]
            Classification timestamp. Defaults to datetime.now().

        Returns
        -------
        RegimeClassification
            Classification result with regime ID, confidence, features, and transition probs.
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

        regime = _REGIME_MAP.get(
            (trend_category, features.volatility_regime, features.volume_regime),
            "R05",  # Default to neutral-normal-normal
        )

        confidence = _compute_confidence(features)
        transition_probs = _compute_transition_probabilities(regime, confidence, features)

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
            transition_probs=transition_probs,
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
        Historical price series (oldest first).
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
]
