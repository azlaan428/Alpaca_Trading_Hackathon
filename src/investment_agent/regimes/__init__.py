"""Regimes Subpackage — Market Regime Taxonomy Layer.

WHAT
====
Defines the canonical set of 12 market regime identifiers (R01 through R12)
used across the X Quant X quantitative intelligence pipeline, and provides
a rule-based regime detector for classifying market conditions.

WHY
===
Market regimes represent distinct macroeconomic and microstructural operating
environments (e.g., bull quiet, bear volatile, crisis deleveraging). Risk
rules, agent reputation weights, and allocation parameters vary by regime.
Centralizing the authoritative set of valid regimes prevents domain invalidity,
regime spoofing, and inconsistent regime validation across modules.

HOW
===
Uses lazy attribute resolution to expose the public API without triggering
circular imports during package initialization.

Architectural Role
==================
Analytical constant and classification module. Defines domain boundaries and
contains no state, side effects, or trading execution code.
"""

from __future__ import annotations

_public_api: dict = {}


def __getattr__(name: str):
    """Lazy import resolver for regimes subpackage namespace."""
    if name in _public_api:
        module_path, attr = _public_api[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module 'investment_agent.regimes' has no attribute {name!r}")


def __dir__() -> list:
    """Return sorted list of public API names for IDE autocompletion."""
    return sorted(set(dir(__builtins__)) | set(_public_api.keys()))


# regimes
_public_api["VALID_REGIMES"] = (
    "investment_agent.regimes.regimes",
    "VALID_REGIMES",
)

# regime_detector
_public_api["RegimeClassification"] = (
    "investment_agent.regimes.regime_detector",
    "RegimeClassification",
)
_public_api["MarketFeatures"] = (
    "investment_agent.regimes.regime_detector",
    "MarketFeatures",
)
_public_api["RegimeDetector"] = (
    "investment_agent.regimes.regime_detector",
    "RegimeDetector",
)
_public_api["detect_regime"] = (
    "investment_agent.regimes.regime_detector",
    "detect_regime",
)

__all__ = list(_public_api.keys())
