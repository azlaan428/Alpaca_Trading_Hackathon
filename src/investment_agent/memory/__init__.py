"""Memory Subpackage — Hedge Decision Persistence & Reflection Layer.

WHAT
====
Provides JSON-backed persistence for hedge trading decisions and reflection
utilities to evaluate past decision outcomes against current market prices.

WHY
===
Enables the hedge signal module to avoid redundant hedges (already_hedged_recently)
and to retrospectively assess hedge effectiveness (reflect) without external
databases or stateful services.

HOW
===
Uses lazy attribute resolution to expose the public API without triggering
circular imports during package initialization.

Architectural Role
==================
Persistence layer for hedge signal decisions. Consumed by the hedge signal
module (signals/hedge_signal.py) to maintain decision history.
"""

from __future__ import annotations

_public_api: dict = {}


def __getattr__(name: str):
    """Lazy import resolver for memory subpackage namespace."""
    if name in _public_api:
        module_path, attr = _public_api[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module 'investment_agent.memory' has no attribute {name!r}")


def __dir__() -> list:
    """Return sorted list of public API names for IDE autocompletion."""
    return sorted(set(dir(__builtins__)) | set(_public_api.keys()))


_public_api["MEMORY_FILE"] = (
    "investment_agent.memory.memory",
    "MEMORY_FILE",
)
_public_api["already_hedged_recently"] = (
    "investment_agent.memory.memory",
    "already_hedged_recently",
)
_public_api["log_decision"] = (
    "investment_agent.memory.memory",
    "log_decision",
)
_public_api["reflect"] = (
    "investment_agent.memory.memory",
    "reflect",
)

__all__ = list(_public_api.keys())
