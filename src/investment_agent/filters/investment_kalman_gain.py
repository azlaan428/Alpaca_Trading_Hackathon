"""Investment Kalman Gain Module — Effective Noise & Gain Modulation Layer for X Quant X.

WHAT
====
Implements the real investment Kalman gain K_t and effective measurement noise variance R_t
derived from multi-agent ensemble effective confidence (c̄_t) and inter-agent disagreement (D_t).

WHY
===
In traditional Kalman filtering, measurement noise R is fixed or exogenous. In the X Quant X
finite-investment architecture, effective measurement noise R_t dynamically reflects ensemble
uncertainty and conflict. When agent disagreement is high or ensemble confidence is low,
effective measurement noise increases, shrinking the investment Kalman gain K_t toward 0.
Conversely, high confidence and low disagreement collapse R_t, driving K_t toward 1.

HOW
===
- compute_effective_measurement_noise(): Calculates R_t = σ²_base * (1 - c̄_t) / c̄_t + D_t² * σ²_base.
  If c̄_t == 0.0, R_t := +∞.
- compute_investment_kalman_gain(): Calculates K_t = P_{t|t-1} / (P_{t|t-1} + R_t).
  If R_t == +∞, K_t := 0.0.

Mathematical Specification
==========================
- Public Judges Whitepaper: Definition 2.3, Theorem 2.4
- Team-Mates Whitepaper: Section 3.3, Proposition 3.1

Architectural Role
==================
Analytical modulation layer. Consumed downstream by the Seven-State Capital Gate to modulate
effective position sizing. Performs no market execution or state mutations.
"""

import math
from typing import Any


def _validate_float_input(val: Any, label: str) -> float:
    """Strictly validate floating point parameters against boolean, non-numeric, NaN, and Inf inputs."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise TypeError(f"{label} must be numeric, got {type(val).__name__}")
    
    val_float = float(val)
    if math.isnan(val_float):
        raise ValueError(f"{label} cannot be NaN")
    if math.isinf(val_float):
        raise ValueError(f"{label} cannot be Infinity")

    return val_float


def compute_effective_measurement_noise(
    effective_confidence: float,
    disagreement: float,
    sigma_base_squared: float = 1.0,
) -> float:
    r"""Compute effective measurement noise covariance R_t.

    R_t = \sigma^2_{base} * (1 - c_bar_t) / c_bar_t + D_t^2 * \sigma^2_{base}

    Per Public Judges Definition 2.3 and Team-Mates Section 3.3.
    When effective_confidence c_bar_t == 0.0, R_t is defined as +Infinity.

    Parameters
    ----------
    effective_confidence : float
        Ensemble effective confidence c_bar_t in [0.0, 1.0].
    disagreement : float
        Inter-agent disagreement metric D_t in [0.0, 2.0] (Theorem 1.4).
    sigma_base_squared : float, optional
        Base model variance \sigma^2_{base} > 0.0 (default 1.0).

    Returns
    -------
    float
        Effective measurement noise R_t >= 0.0 (or math.inf if c_bar_t == 0.0).
    """
    c_bar = _validate_float_input(effective_confidence, "effective_confidence")
    d_t = _validate_float_input(disagreement, "disagreement")
    sigma_sq = _validate_float_input(sigma_base_squared, "sigma_base_squared")

    if sigma_sq <= 0.0:
        raise ValueError(f"sigma_base_squared must be strictly positive (> 0), got {sigma_sq}")

    if c_bar < 0.0 or c_bar > 1.0:
        raise ValueError(f"effective_confidence must lie in [0.0, 1.0], got {c_bar}")

    if d_t < 0.0 or d_t > 2.0:
        raise ValueError(f"disagreement must lie in [0.0, 2.0] per Theorem 1.4, got {d_t}")

    # Limiting case per Definition 2.3: R_t := +inf when c_bar_t = 0.0
    if c_bar == 0.0:
        return math.inf

    r_t = sigma_sq * (1.0 - c_bar) / c_bar + (d_t ** 2) * sigma_sq
    return max(0.0, float(r_t))


def compute_investment_kalman_gain(
    prediction_covariance: float,
    effective_confidence: float,
    disagreement: float,
    sigma_base_squared: float = 1.0,
) -> float:
    r"""Compute investment Kalman gain K_t.

    R_t = compute_effective_measurement_noise(c_bar_t, D_t, \sigma^2_{base})
    K_t = P_{t|t-1} / (P_{t|t-1} + R_t)

    Implements Proposition 3.1 (Team-Mates) and Theorem 2.4 (Public Judges).

    Parameters
    ----------
    prediction_covariance : float
        Prior prediction covariance P_{t|t-1} > 0.0.
    effective_confidence : float
        Ensemble effective confidence c_bar_t in [0.0, 1.0].
    disagreement : float
        Inter-agent disagreement metric D_t in [0.0, 2.0].
    sigma_base_squared : float, optional
        Base model variance \sigma^2_{base} > 0.0 (default 1.0).

    Returns
    -------
    float
        Investment Kalman gain K_t in [0.0, 1.0].
    """
    p_pred = _validate_float_input(prediction_covariance, "prediction_covariance")
    if p_pred <= 0.0:
        raise ValueError(f"prediction_covariance must be strictly positive (> 0), got {p_pred}")

    r_t = compute_effective_measurement_noise(
        effective_confidence=effective_confidence,
        disagreement=disagreement,
        sigma_base_squared=sigma_base_squared,
    )

    if math.isinf(r_t):
        return 0.0

    k_t = p_pred / (p_pred + r_t)
    return max(0.0, min(1.0, float(k_t)))
