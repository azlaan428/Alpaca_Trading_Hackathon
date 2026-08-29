"""Execution Subpackage — Alpaca Broker API Execution Layer.

WHAT
====
Provides order execution functions for the Alpaca paper trading API,
including option contract retrieval, market order placement, and account
summary retrieval.

WHY
===
Encapsulates all broker API interactions in a single module with safety
checks (position sizing limits) to prevent runaway orders during the
hackathon competition.

HOW
===
Uses lazy attribute resolution to expose the public API without triggering
circular imports during package initialization.

Architectural Role
==================
Execution layer. Consumes signals from the capital gate and submits orders
to the Alpaca Broker API. This is the only module with external side-effects
(broker API calls, order placement).
"""

from __future__ import annotations

_public_api: dict = {}


def __getattr__(name: str):
    """Lazy import resolver for execution subpackage namespace."""
    if name in _public_api:
        module_path, attr = _public_api[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module 'investment_agent.execution' has no attribute {name!r}")


def __dir__() -> list:
    """Return sorted list of public API names for IDE autocompletion."""
    return sorted(set(dir(__builtins__)) | set(_public_api.keys()))


_public_api["MAX_POSITION_PCT"] = (
    "investment_agent.execution.execution",
    "MAX_POSITION_PCT",
)
_public_api["get_account_summary"] = (
    "investment_agent.execution.execution",
    "get_account_summary",
)
_public_api["get_option_contract"] = (
    "investment_agent.execution.execution",
    "get_option_contract",
)
_public_api["is_trade_safe"] = (
    "investment_agent.execution.execution",
    "is_trade_safe",
)
_public_api["place_order"] = (
    "investment_agent.execution.execution",
    "place_order",
)

__all__ = list(_public_api.keys())
