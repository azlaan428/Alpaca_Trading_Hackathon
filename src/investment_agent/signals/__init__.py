"""Signals Subpackage — Multi-Agent Signal Aggregation & Hedge Generation.

WHAT
====
Aggregates directional signals from N specialist agents into consensus metrics
and generates protective hedge signals when market conditions deteriorate.

WHY
===
In multi-agent quantitative architecture, combining individual model predictions
into a robust consensus requires weighting by agent reputation and confidence
while explicitly measuring disagreement. The hedge signal module uses price
history to detect significant drawdowns and automatically generate protective
option orders.

HOW
===
Uses lazy attribute resolution to expose the public API without triggering
circular imports during package initialization.

Mathematical Specification
==========================
Specified in:
    - high_level_proofs/high_level_kalman_filter_states_capital_allocation_proof.tex
    - public_team_mates/team_mates_whitepaper.tex

Architectural Role
==================
Analytical consensus and signal generation layers. Consume agent outputs and
reputation weights; produce EnsembleAggregate and hedge orders.
"""

from __future__ import annotations

_public_api: dict = {}


def __getattr__(name: str):
    """Lazy import resolver for signals subpackage namespace."""
    if name in _public_api:
        module_path, attr = _public_api[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module 'investment_agent.signals' has no attribute {name!r}")


def __dir__() -> list:
    """Return sorted list of public API names for IDE autocompletion."""
    return sorted(set(dir(__builtins__)) | set(_public_api.keys()))


# ensemble_signal
_public_api["AgentOutput"] = (
    "investment_agent.signals.ensemble_signal",
    "AgentOutput",
)
_public_api["EnsembleAggregate"] = (
    "investment_agent.signals.ensemble_signal",
    "EnsembleAggregate",
)
_public_api["compute_dampened_signal"] = (
    "investment_agent.signals.ensemble_signal",
    "compute_dampened_signal",
)
_public_api["compute_disagreement"] = (
    "investment_agent.signals.ensemble_signal",
    "compute_disagreement",
)
_public_api["compute_effective_confidence"] = (
    "investment_agent.signals.ensemble_signal",
    "compute_effective_confidence",
)
_public_api["compute_ensemble_aggregate"] = (
    "investment_agent.signals.ensemble_signal",
    "compute_ensemble_aggregate",
)
_public_api["compute_ensemble_signal"] = (
    "investment_agent.signals.ensemble_signal",
    "compute_ensemble_signal",
)

# hedge_signal
_public_api["DROP_THRESHOLD_PCT"] = (
    "investment_agent.signals.hedge_signal",
    "DROP_THRESHOLD_PCT",
)
_public_api["check_for_drop"] = (
    "investment_agent.signals.hedge_signal",
    "check_for_drop",
)
_public_api["get_recent_prices"] = (
    "investment_agent.signals.hedge_signal",
    "get_recent_prices",
)
_public_api["run_hedge_check"] = (
    "investment_agent.signals.hedge_signal",
    "run_hedge_check",
)

__all__ = list(_public_api.keys())
