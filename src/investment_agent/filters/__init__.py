"""Filters Subpackage — Kalman Filter & Investment Kalman Gain Layers.

WHAT
====
Provides state estimation (Kalman filter) and gain modulation (investment
Kalman gain) for the X Quant X quantitative architecture.

WHY
===
The Kalman filter separates true price/trend state from observation noise,
producing posterior estimates and covariance bounds required by the capital
gate. The investment Kalman gain maps ensemble confidence and disagreement
into a capital deployment fraction, dynamically reflecting measurement noise.

HOW
===
Uses lazy attribute resolution to expose the public API without triggering
circular imports during package initialization.

Mathematical Specification
==========================
Specified in:
    - high_level_proofs/finite_investment_architecture_as_economic_financial_fiscal_investment_kalman_filter.md
    - high_level_proofs/high_level_kalman_filter_states_capital_allocation_proof.tex

Architectural Role
==================
Analytical estimation and modulation layers. Consume price observations
and ensemble signals; produce KalmanState and K_t for the capital gate.
Perform no order placement or execution side-effects.
"""

from __future__ import annotations

_public_api: dict = {}


def __getattr__(name: str):
    """Lazy import resolver for filters subpackage namespace."""
    if name in _public_api:
        module_path, attr = _public_api[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module 'investment_agent.filters' has no attribute {name!r}")


def __dir__() -> list:
    """Return sorted list of public API names for IDE autocompletion."""
    return sorted(set(dir(__builtins__)) | set(_public_api.keys()))


_public_api["compute_effective_measurement_noise"] = (
    "investment_agent.filters.investment_kalman_gain",
    "compute_effective_measurement_noise",
)
_public_api["compute_investment_kalman_gain"] = (
    "investment_agent.filters.investment_kalman_gain",
    "compute_investment_kalman_gain",
)
_public_api["KalmanFilter"] = (
    "investment_agent.filters.kalman_filter",
    "KalmanFilter",
)
_public_api["KalmanState"] = (
    "investment_agent.filters.kalman_filter",
    "KalmanState",
)

__all__ = list(_public_api.keys())
