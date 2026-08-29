"""Ensemble Signal Aggregation — Multi-Agent Consensus & Disagreement Layer for X Quant X.

WHAT
====
Aggregates directional signals (s_i), confidence weights (c_i), directional probabilities (p_plus, p_minus),
and reputation weights (w_i) from N specialist agents into an atomic aggregate tuple (S_t, D_t, c̄_t).

WHY
===
In multi-agent quantitative architecture, combining individual model predictions into a robust consensus
requires weighting signals by agent reputation and confidence while explicitly measuring disagreement (D_t)
and effective confidence (c̄_t). To prevent the G-005 mathematical inconsistency vulnerability (where callers
calculate metrics separately using inconsistent signals), aggregation is performed atomically.

HOW
===
- Ensemble Signal: S_t = (1 / W) * ∑_{i=1}^{N} w_i * s_i, where W = ∑ w_i.
- Disagreement Metric: D_t = (1 / W) * ∑_{i=1}^{N} w_i * |s_i - S_t| ∈ [0.0, 2.0].
- Effective Confidence: c̄_t = (1 / W) * ∑_{i=1}^{N} w_i * c_i ∈ [0.0, 1.0].
- Atomic Aggregation: compute_ensemble_aggregate() returns EnsembleAggregate(S_t, D_t, c̄_t) in a single pure step.

Mathematical Specification
==========================
- Public Judges / Team-Mates Whitepapers: Definition 2.1 (Ensemble Signal), Definition 2.2 (Disagreement),
  Definition 2.3 (Effective Confidence), Definition 2.4 (Directional Probabilities).

Architectural Role
==================
Analytical consensus layer. Feeds EnsembleAggregate objects into the Investment Kalman Gain calculation
(investment_kalman_gain.py) and the Seven-State Capital Gate (capital_gate.py). Performs no order placement
or execution side-effects.
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Any


def _validate_float(
    val: Any,
    field_name: str,
    min_val: float = None,
    max_val: float = None,
    exclusive_min: bool = False,
    exclusive_max: bool = False,
) -> float:
    """Strictly validate numeric floating point fields. Rejects bools, non-numeric, NaN, Inf, and out-of-bounds values."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise TypeError(f"{field_name} must be numeric, got {type(val).__name__}")
    
    val_float = float(val)
    if math.isnan(val_float):
        raise ValueError(f"{field_name} cannot be NaN")
    if math.isinf(val_float):
        raise ValueError(f"{field_name} cannot be Infinity")

    if min_val is not None:
        if exclusive_min and val_float <= min_val:
            raise ValueError(f"{field_name} must be > {min_val}, got {val_float}")
        elif not exclusive_min and val_float < min_val:
            raise ValueError(f"{field_name} must be >= {min_val}, got {val_float}")

    if max_val is not None:
        if exclusive_max and val_float >= max_val:
            raise ValueError(f"{field_name} must be < {max_val}, got {val_float}")
        elif not exclusive_max and val_float > max_val:
            raise ValueError(f"{field_name} must be <= {max_val}, got {val_float}")

    return val_float


@dataclass(frozen=True)
class AgentOutput:
    """Frozen, immutable container for a single agent's quantitative signal output (Definition 2.1).

    Attributes
    ----------
    s : float
        Directional signal in [-1.0, 1.0]. -1 = max bearish, +1 = max bullish.
    c : float
        Confidence in directional view in (0.0, 1.0]. Must be strictly > 0.0.
    u : float
        Uncertainty in [0.0, 1.0] when internal signals conflict.
    d : float
        Doubt in [0.0, 1.0] representing historical calibration quality discount.
    p_plus : float
        Estimated probability of a favorable outcome in [0.0, 1.0].
    p_minus : float
        Estimated probability of an unfavorable outcome in [0.0, 1.0].
    delta_t : float
        Investment time horizon in seconds/periods. Must be strictly > 0.0.
    r : float
        Estimated risk or loss exposure. Must be >= 0.0.
    agent_id : str
        Non-empty unique identifier for the emitting agent.
    """

    s: float
    c: float
    u: float
    d: float
    p_plus: float
    p_minus: float
    delta_t: float
    r: float
    agent_id: str

    def __post_init__(self) -> None:
        """Enforce strict domain invariants and type safety upon initialization."""
        s_val = _validate_float(self.s, "s", min_val=-1.0, max_val=1.0)
        c_val = _validate_float(self.c, "c", min_val=0.0, max_val=1.0, exclusive_min=True)
        u_val = _validate_float(self.u, "u", min_val=0.0, max_val=1.0)
        d_val = _validate_float(self.d, "d", min_val=0.0, max_val=1.0)
        p_plus_val = _validate_float(self.p_plus, "p_plus", min_val=0.0, max_val=1.0)
        p_minus_val = _validate_float(self.p_minus, "p_minus", min_val=0.0, max_val=1.0)
        delta_t_val = _validate_float(self.delta_t, "delta_t", min_val=0.0, exclusive_min=True)
        r_val = _validate_float(self.r, "r", min_val=0.0)

        if not isinstance(self.agent_id, str):
            raise TypeError(f"agent_id must be a string, got {type(self.agent_id).__name__}")
        if not self.agent_id.strip():
            raise ValueError("agent_id cannot be empty or whitespace")

        # Probability constraint: p^+ + p^- <= 1.0
        if p_plus_val + p_minus_val > 1.0 + 1e-12:
            raise ValueError(
                f"Probability constraint violated: p_plus ({p_plus_val}) + p_minus ({p_minus_val}) "
                f"= {p_plus_val + p_minus_val} > 1.0"
            )

        # Work around dataclass frozen immutability to store validated floats
        object.__setattr__(self, "s", s_val)
        object.__setattr__(self, "c", c_val)
        object.__setattr__(self, "u", u_val)
        object.__setattr__(self, "d", d_val)
        object.__setattr__(self, "p_plus", p_plus_val)
        object.__setattr__(self, "p_minus", p_minus_val)
        object.__setattr__(self, "delta_t", delta_t_val)
        object.__setattr__(self, "r", r_val)
        object.__setattr__(self, "agent_id", self.agent_id.strip())


# ---------------------------------------------------------------------------
# Ensemble Aggregate Result (G-005: Atomic aggregation to prevent inconsistency)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Numerical tolerance for floating-point boundary checks
# ---------------------------------------------------------------------------
# Floating-point accumulation may produce 1.0000000000000002 for boundary values.
# We permit slippage within machine epsilon (approximately 2.22e-16 for float64).
# Audit philosophy: raise on clear violations, but permit epsilon-level boundary slip.
_FLOAT_TOLERANCE = 1e-10  # Conservative tolerance for accumulation errors


@dataclass(frozen=True)
class EnsembleAggregate:
    """Immutable atomic result of ensemble signal aggregation (G-005 audit fix).
    
    This dataclass ensures S_t, D_t, and c̄_t are computed together from the same
    agents/weights, preventing the mathematical inconsistency where compute_disagreement()
    accepted unverified S_t values.
    
    NOTE (audit): This only eliminates G-005 if callers migrate to this function.
    The deprecated compute_disagreement() still accepts unverified ensemble_signal.
    
    Attributes
    ----------
    ensemble_signal : float
        Aggregated directional signal S_t ∈ [-1.0, 1.0].
    disagreement : float
        Inter-agent disagreement D_t ∈ [0.0, 2.0].
    effective_confidence : float
        Ensemble effective confidence c̄_t ∈ [0.0, 1.0].
    sum_weights : float
        Total positive weight sum Σ w_i > 0 (used by investment Kalman gain).
    """
    ensemble_signal: float
    disagreement: float
    effective_confidence: float
    sum_weights: float
    
    def __post_init__(self) -> None:
        """Validate immutable aggregate bounds with numerical tolerance."""
        # Convert to float like AgentOutput does (not strict isinstance check)
        try:
            s_val = float(self.ensemble_signal)
            d_val = float(self.disagreement)
            c_val = float(self.effective_confidence)
            w_val = float(self.sum_weights)
        except (TypeError, ValueError) as e:
            raise TypeError(f"EnsembleAggregate fields must be numeric: {e}")
        
        # Check for NaN/Inf
        if math.isnan(s_val) or math.isinf(s_val):
            raise ValueError(f"ensemble_signal must be finite, got {s_val}")
        if math.isnan(d_val) or math.isinf(d_val):
            raise ValueError(f"disagreement must be finite, got {d_val}")
        if math.isnan(c_val) or math.isinf(c_val):
            raise ValueError(f"effective_confidence must be finite, got {c_val}")
        if math.isnan(w_val) or math.isinf(w_val):
            raise ValueError(f"sum_weights must be finite, got {w_val}")
        
        # Validate bounds with tolerance for floating-point accumulation.
        # Tolerance distinguishes noise from real violation, then clamp back to domain.
        if s_val < -1.0 - _FLOAT_TOLERANCE or s_val > 1.0 + _FLOAT_TOLERANCE:
            raise ValueError(
                f"ensemble_signal must lie in [-1.0, 1.0] (±{_FLOAT_TOLERANCE} tolerance), "
                f"got {s_val}. This indicates upstream computation error."
            )
        # Clamp to valid domain to eliminate floating-point boundary creep
        s_val = min(1.0, max(-1.0, s_val))
        
        if d_val < -_FLOAT_TOLERANCE or d_val > 2.0 + _FLOAT_TOLERANCE:
            raise ValueError(
                f"disagreement must lie in [0.0, 2.0] (±{_FLOAT_TOLERANCE} tolerance), "
                f"got {d_val}. This indicates upstream computation error."
            )
        # Clamp to valid domain
        d_val = min(2.0, max(0.0, d_val))
        
        if c_val < -_FLOAT_TOLERANCE or c_val > 1.0 + _FLOAT_TOLERANCE:
            raise ValueError(
                f"effective_confidence must lie in [0.0, 1.0] (±{_FLOAT_TOLERANCE} tolerance), "
                f"got {c_val}. This indicates upstream computation error."
            )
        # Clamp to valid domain
        c_val = min(1.0, max(0.0, c_val))
        
        if w_val <= 0.0:
            raise ValueError(
                f"sum_weights must be strictly positive, got {w_val}"
            )
        
        # Write validated, clamped values back to frozen dataclass fields
        object.__setattr__(self, "ensemble_signal", s_val)
        object.__setattr__(self, "disagreement", d_val)
        object.__setattr__(self, "effective_confidence", c_val)
        object.__setattr__(self, "sum_weights", w_val)



def compute_dampened_signal(agent: AgentOutput) -> float:
    """Compute per-agent dampened signal phi_i = s_i * c_i * (1 - u_i) * (1 - d_i).

    Parameters
    ----------
    agent : AgentOutput
        Validated agent signal output.

    Returns
    -------
    float
        Dampened signal guaranteed to lie in [-1.0, 1.0] by mathematical construction.
        Given: s_i ∈[-1,1], c_i ∈(0,1], (1-u_i),(1-d_i)∈[0,1], then |φ_i|≤1 (G-009).
        No runtime clamping needed; that would mask upstream invariant failures.
    """
    if not isinstance(agent, AgentOutput):
        raise TypeError(f"agent must be an AgentOutput instance, got {type(agent).__name__}")

    # Mathematical bound: s_i*c_i*(1-u_i)*(1-d_i) with all factors in documented ranges
    # guarantees |phi| <= 1 without additional clamping.
    phi = agent.s * agent.c * (1.0 - agent.u) * (1.0 - agent.d)
    return float(phi)


def _validate_agents_and_weights(agents: List[AgentOutput], weights: Dict[str, float]) -> float:
    """Validate ensemble agents list and weight dictionary, returning total weight sum.
    
    Validates that agent_ids exactly match weight keys (G-006).
    Rejects duplicate agent IDs (G-001/G-008).
    Enforces w_i > 0 as positive reputation weights (weights may exceed 1.0 for scaling).
    NOTE: Does not enforce cardinality; architecture uses 7 agents but API allows any number >= 1.
    """
    if not isinstance(agents, list):
        raise TypeError(f"agents must be a list, got {type(agents).__name__}")
    if not agents:
        raise ValueError("agents list cannot be empty")
    
    # NOTE: Architecture uses seven-agent ensemble (economic, financial, fiscal, portfolio,
    # fundamental, market, sector specialists), but API does not enforce this cardinality.
    # Tests and future components may use subsets for unit testing or specialized scenarios.
    # Cardinality enforcement belongs to capital_gate.py (seven-state gates), not here.

    if not isinstance(weights, dict):
        raise TypeError(f"weights must be a dict, got {type(weights).__name__}")

    seen_ids = set()
    for agent in agents:
        if not isinstance(agent, AgentOutput):
            raise TypeError(f"All items in agents must be AgentOutput instances, got {type(agent).__name__}")
        # G-001/G-008: Reject duplicate agent IDs
        if agent.agent_id in seen_ids:
            raise ValueError(f"Duplicate agent_id in agents: '{agent.agent_id}'")
        seen_ids.add(agent.agent_id)

    agent_ids = {agent.agent_id for agent in agents}
    weight_keys = set(weights.keys())
    if weight_keys != agent_ids:
        missing = sorted(agent_ids - weight_keys)
        extra = sorted(weight_keys - agent_ids)
        if missing:
            raise ValueError(f"Missing reputation weight for agent_id(s): {missing}")
        if extra:
            raise ValueError(f"Extra weight entries for agent_id(s): {extra}")

    sum_w = 0.0
    for agent in agents:
        w_i = weights[agent.agent_id]
        if isinstance(w_i, bool) or not isinstance(w_i, (int, float)):
            raise TypeError(f"Weight for agent '{agent.agent_id}' must be numeric, got {type(w_i).__name__}")

        w_float = float(w_i)
        if math.isnan(w_float) or math.isinf(w_float):
            raise ValueError(f"Weight for agent '{agent.agent_id}' cannot be NaN or Infinity: {w_float}")
        
        # Enforce w_i > 0 (positive reputation weight). No upper bound: positive scaling is valid.
        # NOTE: If architecture specifies w_i = E[θ_i] ∈ (0, 1] as posterior competence,
        # that is a specification-level contract, not a mathematical necessity for aggregation.
        # Normalized weighted average is well-defined for any w_i > 0.
        if w_float <= 0.0:
            raise ValueError(
                f"Weight for agent '{agent.agent_id}' must be strictly positive (> 0), "
                f"got {w_float}."
            )

        sum_w += w_float

    if sum_w <= 0.0:
        raise ValueError(f"Total weight sum must be strictly positive (> 0), got {sum_w}")

    return sum_w


def compute_ensemble_signal(agents: List[AgentOutput], weights: Dict[str, float]) -> float:
    r"""Compute confidence-weighted, uncertainty-discounted aggregate ensemble signal S_t.

    S_t = ( \sum_i w_i * phi_i ) / ( \sum_i w_i )

    Parameters
    ----------
    agents : List[AgentOutput]
        List of agent outputs.
    weights : Dict[str, float]
        Dictionary mapping agent_id to reputation weight w_i > 0.

    Returns
    -------
    float
        Ensemble signal S_t guaranteed to lie in [-1.0, 1.0] (Theorem 1.4 / Theorem 2.3).
        
    Raises
    ------
    ValueError
        If computed signal violates mathematical bounds (indicates upstream error).
        Does not clamp result; raises instead to expose invariant failures (issue #2).
    """
    sum_w = _validate_agents_and_weights(agents, weights)
    weighted_phi_sum = sum(weights[a.agent_id] * compute_dampened_signal(a) for a in agents)
    
    s_t = weighted_phi_sum / sum_w
    
    # Do NOT clamp; raise if mathematical bounds violated (issue #2).
    # The weighted average of values in [-1, 1] must be in [-1, 1].
    # If not, this indicates upstream computation or invariant violation.
    if s_t < -1.0 or s_t > 1.0:
        raise ValueError(
            f"Computed ensemble signal S_t={s_t} violates mathematical bounds [-1.0, 1.0]. "
            f"This indicates upstream invariant violation or numerical computation error."
        )
    
    return float(s_t)


def compute_disagreement(agents: List[AgentOutput], weights: Dict[str, float], ensemble_signal: float) -> float:
    r"""Compute inter-agent ensemble disagreement D_t.

    D_t = ( \sum_i w_i * |s_i - S_t| ) / ( \sum_i w_i )

    Uses raw directional signal s_i (not dampened phi_i) in the deviation term per
    Definition 2.4 (Team-Mates) and Definition 1.3 (Public Judges).

    🔴 DEPRECATED (G-005 AUDIT VULNERABILITY): NOT RECOMMENDED. Use compute_ensemble_aggregate().
    
    CRITICAL LIMITATION - This function enables the G-005 vulnerability:
    - Accepts ensemble_signal as an external parameter (caller-provided)
    - Does NOT verify that ensemble_signal == compute_ensemble_signal(agents, weights)
    - A caller can pass stale, incorrect, or adversarial ensemble_signal values
    - This function will faithfully compute disagreement around the unverified signal
    - Result is mathematically inconsistent: S_t and D_t not computed from same source
    
    This function only validates that -1 ≤ ensemble_signal ≤ 1, NOT that it's the actual
    ensemble signal for these agents/weights. Architectural compliance requires G-005 to
    be impossible, which requires atomic computation.
    
    For guaranteed correctness, use compute_ensemble_aggregate() which computes S_t, D_t,
    c̄_t together in a single validation context with the same agents/weights (G-005 fix).

    Parameters
    ----------
    agents : List[AgentOutput]
        List of agent outputs.
    weights : Dict[str, float]
        Dictionary mapping agent_id to reputation weight w_i > 0.
    ensemble_signal : float
        Precomputed ensemble signal S_t. 
        WARNING: Must be computed from the same agents/weights. This function cannot verify.
        Use compute_ensemble_aggregate() for atomic, verified computation.

    Returns
    -------
    float
        Disagreement metric D_t guaranteed to lie in [0.0, 2.0] (Theorem 1.4).
        
    Raises
    ------
    ValueError
        If ensemble_signal or computed D_t violates architectural bounds.
    """
    sum_w = _validate_agents_and_weights(agents, weights)
    
    if isinstance(ensemble_signal, bool) or not isinstance(ensemble_signal, (int, float)):
        raise TypeError(f"ensemble_signal must be numeric, got {type(ensemble_signal).__name__}")
    
    s_t = float(ensemble_signal)
    if math.isnan(s_t) or math.isinf(s_t):
        raise ValueError(f"ensemble_signal cannot be NaN or Infinity: {s_t}")
    if s_t < -1.0 or s_t > 1.0:
        raise ValueError(f"ensemble_signal must lie in [-1.0, 1.0], got {s_t}")

    weighted_dev_sum = sum(weights[a.agent_id] * abs(a.s - s_t) for a in agents)
    d_t = weighted_dev_sum / sum_w

    # Do not clamp result; instead raise error if architectural bounds violated (G-010).
    # This detects mismatched ensemble_signal that was not computed from these agents/weights.
    if d_t < 0.0 or d_t > 2.0:
        raise ValueError(
            f"Computed disagreement D_t={d_t} violates architectural bounds [0.0, 2.0]. "
            f"This indicates a malformed ensemble_signal or agents. "
            f"ensemble_signal must be computed from the same agents/weights (G-005 audit)."
        )
    return float(d_t)


def compute_effective_confidence(agents: List[AgentOutput], weights: Dict[str, float]) -> float:
    r"""Compute ensemble effective confidence c_bar_t (Definition 2.3 / Section 3.3).

    c_bar_t = ( \sum_i w_i * c_i * (1 - u_i) * (1 - d_i) ) / ( \sum_i w_i )

    Measures effective certainty of the ensemble independent of direction s_i.

    Parameters
    ----------
    agents : List[AgentOutput]
        List of agent outputs.
    weights : Dict[str, float]
        Dictionary mapping agent_id to reputation weight w_i > 0.

    Returns
    -------
    float
        Effective confidence c_bar_t guaranteed to lie in [0.0, 1.0].
    """
    sum_w = _validate_agents_and_weights(agents, weights)
    weighted_c_sum = sum(
        weights[a.agent_id] * a.c * (1.0 - a.u) * (1.0 - a.d)
        for a in agents
    )
    
    c_bar = weighted_c_sum / sum_w
    
    # Enforce bounds strictly; do not clamp (issue #2).
    if c_bar < 0.0 or c_bar > 1.0:
        raise ValueError(
            f"Computed effective confidence c_bar_t={c_bar} violates bounds [0.0, 1.0]. "
            f"This indicates upstream invariant failure."
        )
    
    return float(c_bar)


def compute_ensemble_aggregate(agents: List[AgentOutput], weights: Dict[str, float]) -> EnsembleAggregate:
    r"""RECOMMENDED: Atomic computation of ensemble triple (S_t, D_t, c̄_t) - G-005 fix.
    
    Computes all three aggregated metrics from the same agents/weights in a single
    validation context, returned as an immutable EnsembleAggregate. This prevents the
    G-005 audit issue where compute_disagreement() accepts unverified ensemble_signal.
    
    Computation semantics:
    
    S_t = ( 1/Σw_i ) * Σ w_i * φ_i    where φ_i = s_i * c_i * (1-u_i) * (1-d_i)
    D_t = ( 1/Σw_i ) * Σ w_i * |s_i - S_t|
    c̄_t = ( 1/Σw_i ) * Σ w_i * c_i * (1-u_i) * (1-d_i)
    
    Atomic computation with single validation pass:
    - Accumulates weighted dampened signal, weighted confidence in first loop
    - Stores (s_i, w_i) pairs during first loop for later use
    - Computes S_t from accumulated totals after loop
    - Calculates D_t from stored pairs using computed S_t (avoids re-iteration)
    - Calculates c̄_t from accumulated totals
    
    NOTE: Not strictly one-pass (stores pairs for later use), but atomically prevents
    orphaned ensemble_signal values and guarantees S_t, D_t, c̄_t mathematical consistency.
    
    LIMITATION (audit point): G-005 fixed only if callers use this function.
    The deprecated compute_disagreement() still accepts unverified ensemble_signal.

    Parameters
    ----------
    agents : List[AgentOutput]
        List of agent outputs (any number >= 1; architecture uses 7 but API doesn't enforce).
    weights : Dict[str, float]
        Dictionary mapping agent_id to reputation weight w_i > 0.

    Returns
    -------
    EnsembleAggregate
        Immutable aggregate containing:
        - ensemble_signal: S_t ∈ [-1, 1]
        - disagreement: D_t ∈ [0, 2]
        - effective_confidence: c̄_t ∈ [0, 1]
        - sum_weights: Σ w_i > 0
        
    Raises
    ------
    ValueError
        If any computed metric violates architectural bounds (accounting for floating-point tolerance).
    """
    # Single validation pass (addresses issue #5: triple validation)
    sum_w = _validate_agents_and_weights(agents, weights)
    
    # Atomic computation with single validation pass
    # Accumulate: weighted dampened signal, weighted confidence, and weighted deviations
    aggregate_phi_sum = 0.0
    aggregate_conf_sum = 0.0
    agent_deviations = []  # Store for D_t calculation after S_t is known
    
    for agent in agents:
        w_i = weights[agent.agent_id]
        phi_i = compute_dampened_signal(agent)
        c_i_dampened = agent.c * (1.0 - agent.u) * (1.0 - agent.d)
        
        aggregate_phi_sum += w_i * phi_i
        aggregate_conf_sum += w_i * c_i_dampened
        # Store raw signal and weight for disagreement calculation
        agent_deviations.append((agent.s, w_i))
    
    # S_t = weighted average of dampened signals
    s_t = aggregate_phi_sum / sum_w
    
    # D_t = weighted average of absolute deviations from S_t (now using computed S_t)
    aggregate_dev_sum = sum(w_i * abs(s_i - s_t) for (s_i, w_i) in agent_deviations)
    d_t = aggregate_dev_sum / sum_w
    
    # c̄_t = weighted average of dampened confidence
    c_bar = aggregate_conf_sum / sum_w
    
    # Validate all three metrics with floating-point tolerance
    if s_t < -1.0 - _FLOAT_TOLERANCE or s_t > 1.0 + _FLOAT_TOLERANCE:
        raise ValueError(
            f"Computed ensemble signal S_t={s_t} violates bounds [-1.0, 1.0] (±{_FLOAT_TOLERANCE}). "
            f"Indicates upstream invariant failure."
        )
    
    if d_t < -_FLOAT_TOLERANCE or d_t > 2.0 + _FLOAT_TOLERANCE:
        raise ValueError(
            f"Computed disagreement D_t={d_t} violates bounds [0.0, 2.0] (±{_FLOAT_TOLERANCE}). "
            f"Indicates upstream invariant failure."
        )
    
    if c_bar < -_FLOAT_TOLERANCE or c_bar > 1.0 + _FLOAT_TOLERANCE:
        raise ValueError(
            f"Computed effective confidence c_bar_t={c_bar} violates bounds [0.0, 1.0] (±{_FLOAT_TOLERANCE}). "
            f"Indicates upstream invariant failure."
        )
    
    return EnsembleAggregate(
        ensemble_signal=float(s_t),
        disagreement=float(d_t),
        effective_confidence=float(c_bar),
        sum_weights=sum_w
    )


