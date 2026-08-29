"""Capital Gate Subpackage — Seven-State Quantitative Intelligence Layer.

WHAT
====
Evaluates the 7-dimensional investment state vector, portfolio allocations,
risk thresholds, and regime constraints to determine capital deployment
permission (pass/fail), gated leverage, and allocation multiplier.

WHY
===
Ensures total capital preservation by gating position allocation through
strict analytical thresholds, soft rule penalty reductions, and hard
circuit-breaker constraints before orders reach execution systems.

HOW
===
Uses lazy attribute resolution to expose the public API without triggering
circular imports during package initialization.

Mathematical Specification
==========================
Specified in:
    - high_level_proofs/finite_investment_architecture_states_of_portfolio_investments_securities_finance_markets_fundamentals_sectors.md
    - high_level_proofs/high_level_kalman_filter_states_capital_allocation_proof.tex

Architectural Role
==================
Analytical gating engine. Consumes KalmanState (filters/kalman_filter.py),
AgentReputationTracker (agents/agent_reputation.py), and EnsembleAggregate
(signals/ensemble_signal.py) outputs to gate risk before execution.
Performs no order placement, broker API calls, or external side-effects.
"""

from __future__ import annotations

_public_api: dict = {}


def __getattr__(name: str):
    """Lazy import resolver for capital subpackage namespace."""
    if name in _public_api:
        module_path, attr = _public_api[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module 'investment_agent.capital' has no attribute {name!r}")


def __dir__() -> list:
    """Return sorted list of public API names for IDE autocompletion."""
    return sorted(set(dir(__builtins__)) | set(_public_api.keys()))


_public_api["CapitalGateResult"] = (
    "investment_agent.capital.capital_gate",
    "CapitalGateResult",
)
_public_api["RiskVerdict"] = (
    "investment_agent.capital.capital_gate",
    "RiskVerdict",
)
_public_api["SevenStateVector"] = (
    "investment_agent.capital.capital_gate",
    "SevenStateVector",
)
_public_api["compute_gating_factor"] = (
    "investment_agent.capital.capital_gate",
    "compute_gating_factor",
)
_public_api["evaluate"] = (
    "investment_agent.capital.capital_gate",
    "evaluate",
)

__all__ = list(_public_api.keys())
