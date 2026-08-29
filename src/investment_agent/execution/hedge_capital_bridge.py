"""Hedge Capital Bridge — Risk-Adjusted Hedge Sizing Adapter for X Quant X.

WHAT
====
Adapts raw hedge signal decisions (drop detection, protective put placement) into
risk-adjusted hedge sizing recommendations using account context, recent hedging
activity, and drop severity.

WHY
===
The hedge signal (`hedge_signal.py`) produces binary-ish decisions: "drop > 3%, buy 1 put."
But risk-aware capital allocation requires modulating hedge size based on:
- Drop severity (bigger drop = bigger hedge)
- Recent hedging activity (already hedged recently = smaller/zero hedge)
- Account buying power constraints (already at position limit = reduced hedge)

This module bridges execution-layer hedge signals with capital-aware sizing
WITHOUT requiring the full analytical pipeline (7 agent outputs, health scores, etc.).

HOW
===
- evaluate_hedge_risk(): Compute risk-adjusted hedge sizing multiplier ∈ [0.0, 1.0]
- compute_hedge_quantity(): Convert multiplier into actual option contract quantity
- Hedging state tracking: remembers recent hedges per symbol to avoid over-hedging

Architectural Role
==================
Execution-layer risk adapter. Sits between hedge_signal.py and execution.py.
Does NOT require capital_gate.py inputs. Does NOT fake agent outputs or health scores.
Consumes only data available to the execution layer: price history, account state,
and internal hedge history.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Lazy imports for optional runtime dependencies (alpaca SDK)
# ---------------------------------------------------------------------------
# hedge_signal.py and execution.py require the alpaca SDK, which may not be
# available in all environments (e.g., unit test runners). We import them
# lazily inside functions rather than at module load time.

def _get_check_for_drop():
    from hedge_signal import check_for_drop, DROP_THRESHOLD_PCT
    return check_for_drop, DROP_THRESHOLD_PCT

def _get_execution_utils():
    from execution import is_trade_safe, MAX_POSITION_PCT, get_option_contract
    return is_trade_safe, MAX_POSITION_PCT, get_option_contract


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum hedge sizing multiplier (always allow at least a partial hedge if risk passes)
_MIN_HEDGE_MULTIPLIER: float = 0.1

# Maximum hedge sizing multiplier (cap at full protective position)
_MAX_HEDGE_MULTIPLIER: float = 1.0

# Default lookback window for recent hedge detection (days)
_DEFAULT_HEDGE_LOOKBACK_DAYS: int = 3

# Minimum drop percentage to trigger any hedge consideration
_MIN_DROP_PCT: float = 0.01  # 1% minimum drop


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HedgeRiskAssessment:
    """Immutable risk assessment result for a hedge decision.

    Attributes
    ----------
    symbol : str
        Underlying symbol being assessed.
    drop_pct : float
        Detected price drop percentage from recent high.
    base_quantity : int
        Base hedge quantity before risk adjustment (typically 1 contract).
    risk_multiplier : float
        Risk-adjusted sizing multiplier ∈ [0.0, 1.0].
    adjusted_quantity : int
        Final hedge quantity after risk adjustment.
    already_hedged_recently : bool
        True if symbol was hedged within the lookback window.
    account_capacity_ratio : float
        Ratio of current trade cost to max allowed position size.
    verdict : str
        Risk verdict: "ALLOW", "REDUCE", or "BLOCK".
    reasons : List[str]
        Human-readable explanations for the verdict.
    """

    symbol: str
    drop_pct: float
    base_quantity: int
    risk_multiplier: float
    adjusted_quantity: int
    already_hedged_recently: bool
    account_capacity_ratio: float
    verdict: str
    reasons: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

class _HedgeStateTracker:
    """Tracks recent hedge activity per symbol to prevent over-hedging."""

    def __init__(self) -> None:
        self._recent_hedges: Dict[str, List[datetime]] = {}

    def record_hedge(self, symbol: str, timestamp: Optional[datetime] = None) -> None:
        """Record that a hedge was placed for `symbol`."""
        if timestamp is None:
            timestamp = datetime.now()
        self._recent_hedges.setdefault(symbol, []).append(timestamp)

    def was_hedged_recently(self, symbol: str, lookback_days: int = _DEFAULT_HEDGE_LOOKBACK_DAYS) -> bool:
        """Check if `symbol` was hedged within the last `lookback_days` days."""
        if symbol not in self._recent_hedges:
            return False

        cutoff = datetime.now() - timedelta(days=lookback_days)
        return any(ts > cutoff for ts in self._recent_hedges[symbol])

    def cleanup(self, max_age_days: int = 30) -> None:
        """Remove hedge records older than `max_age_days` to prevent unbounded growth."""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        for symbol in list(self._recent_hedges.keys()):
            self._recent_hedges[symbol] = [
                ts for ts in self._recent_hedges[symbol] if ts > cutoff
            ]
            if not self._recent_hedges[symbol]:
                del self._recent_hedges[symbol]


# Module-level singleton state tracker
_hedge_state = _HedgeStateTracker()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_hedge_risk(
    symbol: str,
    base_quantity: int = 1,
    lookback_days: int = _DEFAULT_HEDGE_LOOKBACK_DAYS,
    min_drop_pct: float = _MIN_DROP_PCT,
    min_multiplier: float = _MIN_HEDGE_MULTIPLIER,
    max_multiplier: float = _MAX_HEDGE_MULTIPLIER,
) -> HedgeRiskAssessment:
    """Evaluate risk-adjusted hedge sizing for a given symbol.

    WHAT
    ====
    Compute a risk-adjusted hedge quantity and verdict for a protective put order
    based on drop severity, recent hedging activity, and account capacity.

    WHY
    ====
    The raw hedge signal produces binary decisions. Risk-aware execution requires
    modulating hedge size based on multiple factors: larger drops warrant larger
    hedges, but repeated hedging on the same symbol should be reduced, and account
    capacity constraints must be respected.

    HOW
    ===
    1. Detect current price drop using `check_for_drop()`.
    2. Check if symbol was recently hedged via `_hedge_state`.
    3. Compute base risk multiplier from drop severity (closer to threshold = smaller hedge).
    4. Reduce multiplier if recently hedged.
    5. Check account capacity via `is_trade_safe()`.
    6. Compute final adjusted quantity and verdict.

    Parameters
    ----------
    symbol : str
        Underlying symbol to assess.
    base_quantity : int, optional
        Base hedge quantity in contracts (default 1).
    lookback_days : int, optional
        Days to look back for recent hedge detection (default 3).
    min_drop_pct : float, optional
        Minimum drop percentage to consider hedging (default 0.01 = 1%).
    min_multiplier : float, optional
        Minimum risk multiplier floor (default 0.1).
    max_multiplier : float, optional
        Maximum risk multiplier ceiling (default 1.0).

    Returns
    -------
    HedgeRiskAssessment
        Immutable assessment containing verdict, multiplier, adjusted quantity,
        and human-readable reasons.

    Raises
    ------
    ValueError
        If parameters are invalid (negative quantities, invalid ranges).
    TypeError
        If symbol is not a string or quantity is not an integer.

    Time Complexity
    ---------------
    O(1) for state lookup; O(N) for price history fetch where N = days * bars_per_day.

    Space Complexity
    ----------------
    O(1) auxiliary space.

    Cyclomatic Complexity
    ---------------------
    8
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise TypeError(f"symbol must be a non-empty string, got {symbol!r}")

    if not isinstance(base_quantity, int) or base_quantity <= 0:
        raise ValueError(f"base_quantity must be a positive integer, got {base_quantity}")

    if lookback_days < 0:
        raise ValueError(f"lookback_days must be non-negative, got {lookback_days}")

    if min_drop_pct < 0.0 or min_drop_pct > 1.0:
        raise ValueError(f"min_drop_pct must be in [0.0, 1.0], got {min_drop_pct}")

    if min_multiplier < 0.0 or min_multiplier > max_multiplier:
        raise ValueError(f"min_multiplier must be in [0.0, max_multiplier], got {min_multiplier}")

    if max_multiplier <= 0.0 or max_multiplier > 1.0:
        raise ValueError(f"max_multiplier must be in (0.0, 1.0], got {max_multiplier}")

    reasons: List[str] = []

    # 1. Detect drop
    check_for_drop_fn, DROP_THRESHOLD_PCT = _get_check_for_drop()
    dropped, drop_pct = check_for_drop_fn(symbol)
    if not dropped:
        reasons.append(f"No significant drop detected ({drop_pct:.2%} < {DROP_THRESHOLD_PCT:.2%})")
        return HedgeRiskAssessment(
            symbol=symbol,
            drop_pct=drop_pct,
            base_quantity=base_quantity,
            risk_multiplier=0.0,
            adjusted_quantity=0,
            already_hedged_recently=False,
            account_capacity_ratio=0.0,
            verdict="BLOCK",
            reasons=tuple(reasons),
        )

    reasons.append(f"Drop detected: {drop_pct:.2%}")

    # 2. Check recent hedging
    already_hedged = _hedge_state.was_hedged_recently(symbol, lookback_days)
    if already_hedged:
        reasons.append(f"Already hedged {symbol} within last {lookback_days} days")

    # 3. Compute risk multiplier from drop severity
    drop_ratio = drop_pct / DROP_THRESHOLD_PCT if DROP_THRESHOLD_PCT > 0.0 else 1.0
    raw_multiplier = min_multiplier + (max_multiplier - min_multiplier) * min(drop_ratio / 2.0, 1.0)
    risk_multiplier = max(min_multiplier, min(max_multiplier, raw_multiplier))

    # 4. Reduce multiplier if recently hedged
    if already_hedged:
        risk_multiplier *= 0.3
        reasons.append("Reduced multiplier due to recent hedge")

    # 5. Check account capacity
    is_trade_safe_fn, MAX_POSITION_PCT, get_option_contract_fn = _get_execution_utils()
    try:
        contract = get_option_contract_fn(symbol, option_type="put")
        estimated_price = float(contract.close_price or 0.0)
    except Exception:
        estimated_price = 0.0
        reasons.append("Could not fetch option contract price for capacity check")

    account_capacity_ratio = 0.0
    if estimated_price > 0.0:
        trade_cost = base_quantity * estimated_price * 100
        max_allowed = float(os.getenv("MAX_BUYING_POWER", "100000")) * MAX_POSITION_PCT
        account_capacity_ratio = min(trade_cost / max_allowed, 1.0) if max_allowed > 0 else 0.0

        if trade_cost > max_allowed:
            reasons.append(f"BLOCKED: trade cost ${trade_cost:.2f} exceeds limit ${max_allowed:.2f}")
            risk_multiplier = 0.0
        elif account_capacity_ratio > 0.8:
            reasons.append(f"High capacity usage: {account_capacity_ratio:.0%}")
            risk_multiplier *= 0.5

    # 6. Compute final quantity and verdict
    raw_adjusted = int(math.floor(base_quantity * risk_multiplier))
    adjusted_quantity = max(1, raw_adjusted) if risk_multiplier > 0.0 and base_quantity > 0 else 0

    if adjusted_quantity == 0:
        verdict = "BLOCK"
        reasons.append("Final quantity reduced to 0")
    elif already_hedged:
        verdict = "REDUCE"
        reasons.append(f"Reduced due to recent hedge: {adjusted_quantity} contract(s)")
    else:
        verdict = "ALLOW"
        reasons.append(f"Final quantity: {adjusted_quantity} contract(s)")

    return HedgeRiskAssessment(
        symbol=symbol,
        drop_pct=drop_pct,
        base_quantity=base_quantity,
        risk_multiplier=risk_multiplier,
        adjusted_quantity=adjusted_quantity,
        already_hedged_recently=already_hedged,
        account_capacity_ratio=account_capacity_ratio,
        verdict=verdict,
        reasons=tuple(reasons),
    )


def record_hedge_placement(symbol: str) -> None:
    """Record that a hedge was placed for `symbol` in the internal state tracker.

    Parameters
    ----------
    symbol : str
        Underlying symbol that was hedged.

    Raises
    ------
    TypeError
        If symbol is not a string.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise TypeError(f"symbol must be a non-empty string, got {symbol!r}")
    _hedge_state.record_hedge(symbol.strip())


def cleanup_hedge_history(max_age_days: int = 30) -> None:
    """Clean up old hedge history entries to prevent unbounded state growth.

    Parameters
    ----------
    max_age_days : int, optional
        Remove hedge records older than this many days (default 30).
    """
    _hedge_state.cleanup(max_age_days)


def get_recent_hedge_symbols(lookback_days: int = _DEFAULT_HEDGE_LOOKBACK_DAYS) -> List[str]:
    """Return list of symbols hedged within the lookback window.

    Parameters
    ----------
    lookback_days : int, optional
        Lookback period in days (default 3).

    Returns
    -------
    List[str]
        Symbols hedged recently.
    """
    now = datetime.now()
    cutoff = now - timedelta(days=lookback_days)
    return [
        symbol
        for symbol, timestamps in _hedge_state._recent_hedges.items()
        if any(ts > cutoff for ts in timestamps)
    ]


# ---------------------------------------------------------------------------
# Convenience re-exports
# ---------------------------------------------------------------------------

__all__ = [
    "HedgeRiskAssessment",
    "evaluate_hedge_risk",
    "record_hedge_placement",
    "cleanup_hedge_history",
    "get_recent_hedge_symbols",
    "DROP_THRESHOLD_PCT",
]
