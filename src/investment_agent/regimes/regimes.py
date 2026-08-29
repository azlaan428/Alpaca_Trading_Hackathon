"""Market Regime Definitions — Quantitative Taxonomy Layer for X Quant X.

WHAT
====
Defines the canonical set of 12 market regime identifiers (R01 through R12) used across the
X Quant X quantitative intelligence pipeline.

WHY
===
Market regimes represent distinct macroeconomic and microstructural operating environments
(e.g., bull quiet, bear volatile, crisis deleveraging). Risk rules, agent reputation weights,
and allocation parameters vary by regime. Centralizing the authoritative set of valid regimes
prevents domain invalidity, regime spoofing, and inconsistent regime validation across modules.

HOW
===
Provides the immutable set `VALID_REGIMES` containing string identifiers formatted as "R01",
"R02", ..., "R12". Modules validate incoming regime parameters against this set.

Architectural Role
==================
Analytical constant module. It defines domain boundaries and contains no state, side effects,
or trading execution code.
"""

from typing import Set

VALID_REGIMES: Set[str] = {
    f"R{i:02d}" for i in range(1, 13)
}

