from __future__ import annotations

r"""Agent Reputation Tracker — Bayesian Beta-Prior Reputation Layer for X Quant X.

WHAT
====
Tracks per-agent, per-regime Bayesian Beta-prior reputation parameters (α, β) and computes
posterior expectation weights w_i = E[θ_i] = α_i / (α_i + β_i) for each specialist agent.

WHY
===
In a multi-agent quantitative architecture, agents demonstrate varying accuracy across different
market regimes (R01-R12). Rather than static or equal weighting, dynamic Bayesian reputation
tracking enables the system to continuously update agent weights based on historical accuracy,
downweighting agents that perform poorly in specific regimes and upweighting consistent performers.

HOW
===
- Module Import Contract: Employs `from regimes import VALID_REGIMES` as part of the flat root module architecture.
- External Scoring System Boundary: The scoring system evaluates agent prediction accuracy and feeds binary
  outcome signals (y_{i,t} ∈ {0, 1}) into the tracker: scoring system → y_{i,t} ∈ {0,1} → reputation tracker.
  This module does NOT evaluate prediction correctness itself (accepted as authoritative upstream input).
- External Emission-Time Regime Contract: Caller must supply the active regime at prediction emission time t
  (not realization time t + Δt). This is an external workflow contract, as the tracker does not store timestamps.
- String Normalization Protocol: Agent IDs are user-defined strings and are stripped of surrounding whitespace.
  Regime identifiers are canonical system constants (`VALID_REGIMES`) and must match strictly without whitespace modification.
- Parameter Capacity Cap: Enforces MAX_PARAM_VALUE = 1e12 on α and β state variables as an explicit
  implementation state-space capacity bound designed to maintain float arithmetic stability. This is an
  implementation constraint, not a mathematical requirement of the Beta-Bernoulli model. The authoritative
  reputation model defines α_{i,r} = α^0_{i,r} + k and β_{i,r} = β^0_{i,r} + (n-k) with no upper bound.
  For a given (agent, regime) pair with priors (α^0, β^0), the maximum number of observations under
  this implementation constraint is approximately (MAX_PARAM_VALUE - α^0) + (MAX_PARAM_VALUE - β^0).
  The _observations counter has no independent cap but is indirectly bounded through record_outcome()
  parameter validation. Initializing a prior at 1e12 puts that parameter immediately at capacity.
- Pre-Mutation Validation & Candidate State Computation: State updates in `record_outcome()` compute and validate
  all candidate state variables prior to dictionary mutation, ensuring no state changes occur on error.
- Consistent Defensive Inspection: `get_reputation_weight()`, `get_posterior_parameters()`, `get_posterior_variance()`,
  and `get_observation_count()` defensively verify internal state variables before returning values.
- Closed Schema & Absolute Invariant Persistence: `from_dict()` enforces closed schemas (rejecting unexpected keys)
  and strict absolute error bounds (|Δα - round(Δα)| ≤ 1e-9) without relative tolerance leakage.
- Single-Threaded Execution Contract: The tracker assumes single-threaded, sequential pipeline execution.
  Concurrent access requires external locking.

Mathematical Specification
==========================
- Team-Mates Whitepaper: Definition 8.1 / Section 8 (Beta-prior reputation system)

Architectural Role
==================
Analytical reputation tracking layer. Feeds weight dictionaries into ensemble signal aggregation
(ensemble_signal.py) and the Seven-State Capital Gate (capital_gate.py). Performs no order
execution or API calls.
"""

import math
from typing import Dict, List, Any, Union
from ..regimes.regimes import VALID_REGIMES

# Implementation state-space capacity cap for prior and posterior alpha/beta parameters.
# Caps individual alpha and beta state variables at 1e12 to ensure floating-point arithmetic stability
# and prevent extreme magnitude numerical underflow/overflow across long-running updates.
MAX_PARAM_VALUE: float = 1e12


def _validate_float_param(val: Any, label: str) -> float:
    """Validate prior alpha/beta parameter values strictly."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise TypeError(f"{label} must be numeric, got {type(val).__name__}")
    
    try:
        val_float = float(val)
    except OverflowError:
        raise ValueError(f"{label} exceeds maximum allowed state capacity ({MAX_PARAM_VALUE:e}), got integer too large for float")

    if math.isnan(val_float):
        raise ValueError(f"{label} cannot be NaN")
    if math.isinf(val_float):
        raise ValueError(f"{label} cannot be Infinity")
    if val_float <= 0.0:
        raise ValueError(f"{label} must be strictly positive (> 0), got {val_float}")
    if val_float > MAX_PARAM_VALUE:
        raise ValueError(f"{label} exceeds maximum allowed state capacity ({MAX_PARAM_VALUE:e}), got {val_float:e}")

    return val_float


class AgentReputationTracker:
    r"""Tracks Bayesian Beta-prior reputation weights for agents across market regimes.

    Implements Definition 8.1 (Team-Mates whitepaper).

    System Boundaries, Contracts, & Threading Contract:
    ---------------------------------------------------
    1. Scoring Process Separation (External Contract):
       This tracker does NOT evaluate prediction correctness or enforce scoring rules. An external
       scoring system evaluates prediction outcomes and passes binary boolean signals (`was_correct`)
       to `record_outcome()`:
           Scoring System → y_{i,t} ∈ {0, 1} → AgentReputationTracker.record_outcome()

    2. Emission-Time Regime Alignment (External Contract):
       The caller must pass the regime active at prediction emission time. Because this module
       does not store prediction lineage or timestamps, regime alignment is an external workflow contract.

    3. Implementation Capacity Cap & State Invariants:
       The tracker stores `alpha`, `beta`, and `observations`. Individual parameter values are capped at 1e12 as an
       explicit implementation capacity bound. This is an engineering safeguard, not a mathematical requirement
       of the Beta-Bernoulli model. The authoritative model defines α = α_0 + k and β = β_0 + (n - k) with
       no upper bound. The Beta-Bernoulli identity is maintained across updates and validated during `from_dict()`
       deserialization with absolute error bounds (|Δα - round(Δα)| <= 1e-9). Initializing prior_alpha or prior_beta
       at 1e12 puts that parameter at the implementation capacity boundary.

    4. String Normalization Distinction:
       User-defined agent IDs are stripped of surrounding whitespace (`agent_id.strip()`).
       Regime IDs are canonical identifiers (`VALID_REGIMES`) and must match strictly without whitespace modifications.

    5. Concurrency & Pre-Mutation Validation:
       `record_outcome()` computes all candidate state variables and validates capacity bounds prior to dictionary mutation.
       This class assumes single-threaded, sequential pipeline execution. If used in a multi-threaded workflow,
       caller-side synchronization (e.g. `threading.Lock`) must surround tracker updates.

    Prior: \rho_{i,r} ~ Beta(\alpha_{i,r}^0, \beta_{i,r}^0)
    Posterior: \alpha_{i,r} = \alpha_{i,r}^0 + k,  \beta_{i,r} = \beta_{i,r}^0 + (n - k)
    Posterior mean: \hat{\rho}_{i,r} = \frac{\alpha_{i,r}}{\alpha_{i,r} + \beta_{i,r}}
    """

    def __init__(
        self,
        agent_ids: List[str],
        regimes: List[str],
        prior_alpha: Union[float, Dict[Any, float]] = 1.0,
        prior_beta: Union[float, Dict[Any, float]] = 1.0,
    ) -> None:
        r"""Initialize Beta priors for every (agent_id, regime) pair.

        WHAT
        ====
        Construct the Bayesian reputation tracker by initializing Beta(α, β) priors
        for each registered (agent, regime) combination. Supports scalar priors or
        indexed prior dictionaries per (agent, regime) pair as specified in Definition 8.1.

        WHY
        ===
        Establishes the prior belief state before any prediction outcomes are observed.
        Default Beta(1,1) encodes uniform ignorance; custom priors encode domain expertise.

        HOW
        ===
        1. Validate agent_ids and regimes type (list) and non-emptiness.
        2. Clean and deduplicate agent IDs (strip whitespace, reject delimiter '|').
        3. Validate regimes against VALID_REGIMES canonical set.
        4. Validate prior_alpha and prior_beta against type, finite, positive, and capacity constraints.
        5. Allocate state dictionaries for alpha, beta, and observations.

        Parameters
        ----------
        agent_ids : List[str]
            List of unique agent identifiers to track.
        regimes : List[str]
            List of unique valid regime identifiers (e.g. R01..R12).
        prior_alpha : Union[float, Dict[Any, float]], optional
            Prior alpha parameter > 0.0 (default 1.0), scalar or dict mapping (agent_id, regime) -> float.
            Capped at MAX_PARAM_VALUE = 1e12 as an implementation capacity constraint.
        prior_beta : Union[float, Dict[Any, float]], optional
            Prior beta parameter > 0.0 (default 1.0), scalar or dict mapping (agent_id, regime) -> float.
            Capped at MAX_PARAM_VALUE = 1e12 as an implementation capacity constraint.

        Returns
        -------
        None

        Raises
        ------
        TypeError
            If agent_ids or regimes are not lists or contain non-string elements, or if priors are non-numeric.
        ValueError
            If agent_ids or regimes are empty lists, contain duplicates, or contain invalid regime identifiers.
            If prior_alpha or prior_beta are non-positive, non-finite, or exceed MAX_PARAM_VALUE.

        Time Complexity
        ---------------
        O(A + R) where A = len(agent_ids), R = len(regimes).

        Space Complexity
        ----------------
        O(AR) auxiliary space for the internal state dictionaries, where A = number of agents
        and R = number of regimes.

        Cyclomatic Complexity
        ---------------------
        10
        """
        if not isinstance(agent_ids, list):
            raise TypeError(f"agent_ids must be a list of strings, got {type(agent_ids).__name__}")
        if not agent_ids:
            raise ValueError("agent_ids must be a non-empty list of strings")

        if not isinstance(regimes, list):
            raise TypeError(f"regimes must be a list of strings, got {type(regimes).__name__}")
        if not regimes:
            raise ValueError("regimes must be a non-empty list of strings")

        cleaned_agents = []
        for aid in agent_ids:
            if not isinstance(aid, str) or not aid.strip():
                raise TypeError(f"All agent_ids must be non-empty strings, got {aid}")
            stripped = aid.strip()
            if "|" in stripped:
                raise ValueError(f"agent_id '{stripped}' cannot contain '|' as it is the state-key delimiter")
            cleaned_agents.append(stripped)

        if len(cleaned_agents) != len(set(cleaned_agents)):
            raise ValueError("agent_ids must be unique (duplicate agent ID detected)")

        cleaned_regimes = []
        for r in regimes:
            if not isinstance(r, str) or r not in VALID_REGIMES:
                raise ValueError(f"Invalid regime identifier '{r}'. Must be one of {sorted(VALID_REGIMES)}")
            cleaned_regimes.append(r)

        if len(cleaned_regimes) != len(set(cleaned_regimes)):
            raise ValueError("regimes must be unique (duplicate regime detected)")

        self._registered_agents = set(cleaned_agents)
        self._registered_regimes = set(cleaned_regimes)

        # Storage initialization
        self._alpha: Dict[tuple[str, str], float] = {}
        self._beta: Dict[tuple[str, str], float] = {}
        self._observations: Dict[tuple[str, str], int] = {}

        # Prior resolution
        is_dict_alpha = isinstance(prior_alpha, dict)
        is_dict_beta = isinstance(prior_beta, dict)

        if not is_dict_alpha:
            single_alpha = _validate_float_param(prior_alpha, "prior_alpha")
            self._prior_alpha = single_alpha
        else:
            self._prior_alpha = 1.0  # Fallback baseline prior for serialization

        if not is_dict_beta:
            single_beta = _validate_float_param(prior_beta, "prior_beta")
            self._prior_beta = single_beta
        else:
            self._prior_beta = 1.0  # Fallback baseline prior for serialization

        for aid in self._registered_agents:
            for r in self._registered_regimes:
                key = (aid, r)
                if is_dict_alpha:
                    val_a = prior_alpha.get(key, prior_alpha.get(aid, 1.0))
                    a_init = _validate_float_param(val_a, f"prior_alpha for ({aid}, {r})")
                else:
                    a_init = single_alpha

                if is_dict_beta:
                    val_b = prior_beta.get(key, prior_beta.get(aid, 1.0))
                    b_init = _validate_float_param(val_b, f"prior_beta for ({aid}, {r})")
                else:
                    b_init = single_beta

                self._alpha[key] = a_init
                self._beta[key] = b_init
                self._observations[key] = 0

    def record_outcome(self, agent_id: str, regime: str, was_correct: bool) -> None:
        r"""Update posterior Beta distribution after observing a prediction outcome.

        WHAT
        ====
        Record a binary prediction outcome (correct/incorrect) and update the posterior
        Beta distribution parameters for the specified (agent_id, regime) pair.

        WHY
        ====
        The Bayesian reputation system accumulates evidence about agent accuracy per regime.
        Each correct outcome increments α by 1; each incorrect outcome increments β by 1.
        This drives the posterior mean weight w = α/(α+β) toward 1.0 for accurate agents
        and toward 0.0 for inaccurate agents.

        HOW
        ===
        1. Validate agent_id, regime, and was_correct against registered sets and types.
        2. Compute candidate state: new_alpha = curr_alpha + 1 (if correct) or unchanged;
           new_beta = curr_beta + 1 (if incorrect) or unchanged.
        3. Enforce implementation capacity: reject update if the target parameter is already
           at MAX_PARAM_VALUE = 1e12. This is an engineering safeguard, not a mathematical
           requirement of the Beta-Bernoulli model.
        4. Validate all candidate state variables prior to dictionary mutation.
        5. Atomically commit the new state to internal dictionaries.

        Parameters
        ----------
        agent_id : str
            Identifier of the emitting agent.
        regime : str
            Regime identifier at prediction emission time.
        was_correct : bool
            True if upstream scoring rule marked prediction as correct/favorable, False otherwise.

        Returns
        -------
        None

        Raises
        ------
        KeyError
            If agent_id or regime is not registered with this tracker.
        TypeError
            If was_correct is not a boolean.
        OverflowError
            If the target parameter (alpha for correct, beta for incorrect) has reached
            the implementation capacity limit of 1e12.

        Notes
        -----
        Regime-time correctness is an external pipeline invariant: the caller must supply
        the regime active at prediction emission time t (not realization time t + Δt).
        This module does not store timestamps or prediction lineage.

        Time Complexity
        ---------------
        O(1) dictionary lookup and arithmetic.

        Space Complexity
        ----------------
        O(1) auxiliary space.

        Cyclomatic Complexity
        ---------------------
        7
        """
        if not isinstance(agent_id, str) or agent_id.strip() not in self._registered_agents:
            raise KeyError(f"Unregistered agent_id '{agent_id}'.")

        if not isinstance(regime, str) or regime not in self._registered_regimes:
            raise KeyError(f"Unregistered regime '{regime}'.")

        if not isinstance(was_correct, bool):
            raise TypeError(f"was_correct must be a boolean, got {type(was_correct).__name__}")

        key = (agent_id.strip(), regime)
        curr_alpha = self._alpha[key]
        curr_beta = self._beta[key]
        curr_obs = self._observations[key]

        if was_correct:
            if curr_alpha >= MAX_PARAM_VALUE:
                raise OverflowError(
                    f"Alpha parameter for key {key} has reached implementation capacity limit ({MAX_PARAM_VALUE:e}). "
                    f"Further updates rejected."
                )
            new_alpha = curr_alpha + 1.0
            if new_alpha <= curr_alpha or new_alpha > MAX_PARAM_VALUE:
                raise OverflowError(
                    f"Alpha parameter update for key {key} saturated floating-point precision or exceeded capacity."
                )
            new_beta = curr_beta
        else:
            if curr_beta >= MAX_PARAM_VALUE:
                raise OverflowError(
                    f"Beta parameter for key {key} has reached implementation capacity limit ({MAX_PARAM_VALUE:e}). "
                    f"Further updates rejected."
                )
            new_beta = curr_beta + 1.0
            if new_beta <= curr_beta or new_beta > MAX_PARAM_VALUE:
                raise OverflowError(
                    f"Beta parameter update for key {key} saturated floating-point precision or exceeded capacity."
                )
            new_alpha = curr_alpha

        new_obs = curr_obs + 1

        # Explicit validation of candidate state parameters prior to dictionary mutation
        _validate_float_param(new_alpha, "candidate alpha")
        _validate_float_param(new_beta, "candidate beta")
        if isinstance(new_obs, bool) or not isinstance(new_obs, int) or new_obs < 0:
            raise ValueError(f"Invalid candidate observation count: {new_obs}")

        # Candidate state application after full pre-validation
        self._alpha[key] = new_alpha
        self._beta[key] = new_beta
        self._observations[key] = new_obs

    def get_reputation_weight(self, agent_id: str, regime: str) -> float:
        r"""Return posterior mean reputation weight w_i for a given agent and regime.

        WHAT
        ====
        Compute the posterior expectation of the Beta distribution for a specific (agent, regime)
        pair: w_i = E[θ_i] = α_i / (α_i + β_i).

        WHY
        ====
        The posterior mean weight is the point estimate of agent competence in a given regime.
        It is used by ensemble_signal.py to weight agent directional signals and by
        investment_kalman_gain.py to modulate capital allocation.

        HOW
        ===
        1. Validate agent_id and regime against registered sets.
        2. Retrieve alpha and beta from internal state dictionaries.
        3. Defensively verify parameters are finite, positive, and within implementation capacity.
        4. Compute weight = alpha / (alpha + beta).
        5. Defensively verify weight lies in the mathematically valid open interval (0, 1).
           Numerical rounding may produce values arbitrarily close to 0 or 1; these are accepted.

        Parameters
        ----------
        agent_id : str
            Identifier of the agent.
        regime : str
            Regime identifier.

        Returns
        -------
        float
            Posterior mean weight w_i ∈ (0.0, 1.0).

        Raises
        ------
        KeyError
            If agent_id or regime is not registered.
        ValueError
            If internal state parameters are non-finite, non-positive, exceed MAX_PARAM_VALUE,
            or if the computed weight is numerically out of bounds.

        Time Complexity
        ---------------
        O(1) dictionary lookup and arithmetic.

        Space Complexity
        ----------------
        O(1) auxiliary space.

        Cyclomatic Complexity
        ---------------------
        5
        """
        if not isinstance(agent_id, str) or agent_id.strip() not in self._registered_agents:
            raise KeyError(f"Unregistered agent_id '{agent_id}'.")

        if not isinstance(regime, str) or regime not in self._registered_regimes:
            raise KeyError(f"Unregistered regime '{regime}'.")

        key = (agent_id.strip(), regime)
        a = self._alpha[key]
        b = self._beta[key]

        if not math.isfinite(a) or not math.isfinite(b) or a <= 0.0 or b <= 0.0:
            raise ValueError(f"Non-finite or non-positive posterior parameters for {key}: alpha={a}, beta={b}")

        if a > MAX_PARAM_VALUE or b > MAX_PARAM_VALUE:
            raise ValueError(
                f"Posterior parameter exceeds implementation capacity for {key}: "
                f"alpha={a:e}, beta={b:e} (cap={MAX_PARAM_VALUE:e})"
            )

        denom = a + b
        if denom <= 0.0 or not math.isfinite(denom):
            raise ValueError(f"Non-positive or non-finite posterior denominator for {key}: {denom}")

        weight = a / denom
        if not math.isfinite(weight):
            raise ValueError(f"Posterior mean weight is non-finite for {key}: {weight}")

        # Enforce open interval (0.0, 1.0) contract against IEEE 754 precision boundary rounding
        if weight <= 0.0:
            weight = 1e-15
        elif weight >= 1.0:
            weight = 1.0 - 1e-15

        return float(weight)

    def get_posterior_parameters(self, agent_id: str, regime: str) -> Dict[str, float]:
        r"""Return current posterior Beta parameters for a given agent and regime.

        WHAT
        ====
        Retrieve the current alpha and beta values of the Beta posterior distribution
        for a specific (agent, regime) pair.

        WHY
        ====
        Posterior parameters are the raw state from which all derived metrics (weight, variance)
        are computed. Exposing them enables external inspection, serialization verification,
        and mathematical auditing.

        HOW
        ===
        1. Validate agent_id and regime against registered sets.
        2. Retrieve alpha and beta from internal state dictionaries.
        3. Defensively verify parameters are finite, positive, and within implementation capacity.
        4. Return as a dictionary with keys 'alpha' and 'beta'.

        Parameters
        ----------
        agent_id : str
            Identifier of the agent.
        regime : str
            Regime identifier.

        Returns
        -------
        Dict[str, float]
            Dictionary with keys 'alpha' and 'beta'.

        Raises
        ------
        KeyError
            If agent_id or regime is not registered.
        ValueError
            If internal state parameters are non-finite, non-positive, or exceed MAX_PARAM_VALUE.

        Time Complexity
        ---------------
        O(1) dictionary lookup.

        Space Complexity
        ----------------
        O(1) auxiliary space for the returned dictionary.

        Cyclomatic Complexity
        ---------------------
        3
        """
        if not isinstance(agent_id, str) or agent_id.strip() not in self._registered_agents:
            raise KeyError(f"Unregistered agent_id '{agent_id}'.")

        if not isinstance(regime, str) or regime not in self._registered_regimes:
            raise KeyError(f"Unregistered regime '{regime}'.")

        key = (agent_id.strip(), regime)
        a = self._alpha[key]
        b = self._beta[key]

        if not math.isfinite(a) or not math.isfinite(b) or a <= 0.0 or b <= 0.0:
            raise ValueError(f"Non-finite or non-positive posterior parameters for {key}: alpha={a}, beta={b}")

        if a > MAX_PARAM_VALUE or b > MAX_PARAM_VALUE:
            raise ValueError(
                f"Posterior parameter exceeds implementation capacity for {key}: "
                f"alpha={a:e}, beta={b:e} (cap={MAX_PARAM_VALUE:e})"
            )

        return {
            "alpha": float(a),
            "beta": float(b),
        }

    def get_posterior_variance(self, agent_id: str, regime: str) -> float:
        r"""Return analytical variance of the posterior Beta distribution.

        WHAT
        ====
        Compute the variance of the Beta posterior distribution for a specific (agent, regime) pair.

        WHY
        ====
        Variance measures the uncertainty of the reputation estimate. High variance indicates
        insufficient observations; low variance indicates a well-calibrated reputation estimate.
        Used by ensemble_signal.py and capital_gate.py to assess agent reliability.

        HOW
        ===
        Uses the numerically stable ratio formulation:
        Var(ρ) = (α / total) * (β / total) / (total + 1)
        where total = α + β.

        For valid finite positive alpha and beta, the mathematical variance is strictly positive.
        However, floating-point arithmetic can underflow to 0.0 for extremely imbalanced parameters
        (e.g., α = 1e12, β = 1e-300). This is treated as an explicit numerical boundary of the
        implementation: var == 0.0 is permitted when it results from underflow of a mathematically
        positive variance.

        Parameters
        ----------
        agent_id : str
            Identifier of the agent.
        regime : str
            Regime identifier.

        Returns
        -------
        float
            Posterior variance >= 0.0. Strictly positive for well-behaved parameters; may be 0.0
            due to floating-point underflow for extremely imbalanced parameters.

        Raises
        ------
        KeyError
            If agent_id or regime is not registered.
        ValueError
            If internal state parameters are non-finite, non-positive, or exceed MAX_PARAM_VALUE.
            If the computed variance is non-finite or negative (should not occur for valid inputs).

        Time Complexity
        ---------------
        O(1) arithmetic operations.

        Space Complexity
        ----------------
        O(1) auxiliary space.

        Cyclomatic Complexity
        ---------------------
        3
        """
        params = self.get_posterior_parameters(agent_id, regime)
        a = params["alpha"]
        b = params["beta"]

        if a > MAX_PARAM_VALUE or b > MAX_PARAM_VALUE:
            raise ValueError(
                f"Posterior parameter exceeds implementation capacity for ({agent_id}, {regime}): "
                f"alpha={a:e}, beta={b:e} (cap={MAX_PARAM_VALUE:e})"
            )

        total = a + b
        if not math.isfinite(total) or total <= 0.0:
            raise ValueError(f"Invalid posterior parameter total for ({agent_id}, {regime}): {total}")

        var = (a / total) * (b / total) / (total + 1.0)
        if not math.isfinite(var):
            raise ValueError(f"Posterior variance is non-finite for ({agent_id}, {regime}): {var}")
        if var < 0.0:
            raise ValueError(f"Posterior variance is negative for ({agent_id}, {regime}): {var}")

        return float(var)

    def get_observation_count(self, agent_id: str, regime: str) -> int:
        r"""Return total observation count recorded for an (agent_id, regime) pair.

        WHAT
        ====
        Retrieve the number of prediction outcomes (correct + incorrect) recorded for a
        specific (agent, regime) pair.

        WHY
        ====
        Observation count provides a measure of confidence in the reputation estimate.
        It is used for serialization validation and external auditing.

        HOW
        ===
        1. Validate agent_id and regime against registered sets.
        2. Retrieve the observation count from the internal dictionary.
        3. Defensively verify the count is a non-negative integer.

        Parameters
        ----------
        agent_id : str
            Identifier of the agent.
        regime : str
            Regime identifier.

        Returns
        -------
        int
            Total observation count n >= 0.

        Raises
        ------
        KeyError
            If agent_id or regime is not registered.
        ValueError
            If the internal observation count is corrupted (non-integer or negative).

        Time Complexity
        ---------------
        O(1) dictionary lookup.

        Space Complexity
        ----------------
        O(1) auxiliary space.

        Cyclomatic Complexity
        ---------------------
        3
        """
        if not isinstance(agent_id, str) or agent_id.strip() not in self._registered_agents:
            raise KeyError(f"Unregistered agent_id '{agent_id}'.")

        if not isinstance(regime, str) or regime not in self._registered_regimes:
            raise KeyError(f"Unregistered regime '{regime}'.")

        key = (agent_id.strip(), regime)
        obs = self._observations[key]
        if isinstance(obs, bool) or not isinstance(obs, int) or obs < 0:
            raise ValueError(f"Invalid internal observation count for key {key}: {obs}")

        return int(obs)

    def get_all_weights(self, regime: str) -> Dict[str, float]:
        r"""Return reputation weights for all agents in a given regime.

        WHAT
        =====
        Compute and return a dictionary mapping every registered agent_id to its posterior
        mean reputation weight for the specified regime.

        WHY
        ====
        Provides the complete weight vector required by ensemble_signal.py for weighted
        signal aggregation and by capital_gate.py for risk evaluation.

        HOW
        ===
        Iterate over all registered agent IDs in sorted order (for deterministic output)
        and compute each agent's reputation weight via get_reputation_weight().

        Parameters
        ----------
        regime : str
            Target regime identifier.

        Returns
        -------
        Dict[str, float]
            Dictionary of {agent_id: reputation_weight} for all registered agents.

        Raises
        ------
        KeyError
            If regime is not registered.
        ValueError
            If any agent's internal state parameters are invalid (propagated from
            get_reputation_weight()).

        Time Complexity
        ---------------
        O(A log A) where A = number of registered agents, due to sorted iteration.

        Space Complexity
        ----------------
        O(A) auxiliary space for the returned dictionary, where A = number of agents.

        Cyclomatic Complexity
        ---------------------
        2
        """
        if not isinstance(regime, str) or regime not in self._registered_regimes:
            raise KeyError(f"Unregistered regime '{regime}'.")

        return {
            aid: self.get_reputation_weight(aid, regime)
            for aid in sorted(self._registered_agents)
        }

    def get_normalized_weights(self, regime: str) -> Dict[str, float]:
        r"""Return normalized posterior mean reputation weights (\sum w_i = 1.0) for all agents in a regime.

        WHAT
        ====
        Compute and return a dictionary mapping every registered agent_id to its normalized
        reputation weight w_i / \sum_k w_k for the specified regime.

        WHY
        ====
        While get_all_weights() returns raw posterior expectations w_i \in (0.0, 1.0), downstream ensemble
        aggregation algorithms require normalized weight vectors summing to 1.0 over active agents.

        HOW
        ===
        1. Obtain raw weights via get_all_weights(regime).
        2. Compute total weight sum W = \sum_i w_i.
        3. Divide each weight by W to produce normalized probabilities summing strictly to 1.0.

        Parameters
        ----------
        regime : str
            Target regime identifier.

        Returns
        -------
        Dict[str, float]
            Dictionary of {agent_id: normalized_weight} summing to 1.0 for all registered agents.

        Raises
        ------
        KeyError
            If regime is not registered.
        ValueError
            If the total weight sum is non-positive or non-finite.

        Time Complexity
        ---------------
        O(A log A) where A = number of registered agents.

        Space Complexity
        ----------------
        O(A) auxiliary space for the returned dictionary.

        Cyclomatic Complexity
        ---------------------
        2
        """
        raw_weights = self.get_all_weights(regime)
        total_w = sum(raw_weights.values())
        if total_w <= 0.0 or not math.isfinite(total_w):
            raise ValueError(f"Invalid total weight sum for regime '{regime}': {total_w}")

        return {aid: w / total_w for aid, w in raw_weights.items()}

    def to_dict(self) -> Dict[str, Any]:
        r"""Serialize complete tracker state to a dictionary for persistence.

        WHAT
        ====
        Convert the entire internal state (registered agents, regimes, priors, and all
        per-pair alpha/beta/observations) into a JSON-serializable dictionary.

        WHY
        ====
        Enables state persistence across process restarts, audit logging, and checkpointing.
        The serialized format is consumed by from_dict() for exact state reconstruction.

        HOW
        ===
        Construct a dictionary with sorted agent_ids and regimes (for deterministic output),
        prior values, and a nested state map keyed by 'agent_id|regime' strings.

        Returns
        -------
        Dict[str, Any]
            Serializable state dictionary with structure:
            {
                'agent_ids': List[str],
                'regimes': List[str],
                'prior_alpha': float,
                'prior_beta': float,
                'state': Dict[str, Dict[str, Any]]
            }

        Raises
        ------
        None

        Time Complexity
        ---------------
        O(AR log A + AR log R) where A = number of agents and R = number of regimes,
        due to sorted iteration over agents and regimes in the state comprehension.

        Space Complexity
        ----------------
        O(AR) auxiliary space for the returned dictionary, where A = number of agents
        and R = number of regimes.

        Cyclomatic Complexity
        ---------------------
        1
        """
        return {
            "agent_ids": sorted(self._registered_agents),
            "regimes": sorted(self._registered_regimes),
            "prior_alpha": self._prior_alpha,
            "prior_beta": self._prior_beta,
            "state": {
                f"{aid}|{r}": {
                    "alpha": self._alpha[(aid, r)],
                    "beta": self._beta[(aid, r)],
                    "observations": self._observations[(aid, r)],
                }
                for aid in sorted(self._registered_agents)
                for r in sorted(self._registered_regimes)
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentReputationTracker:
        r"""Reconstruct AgentReputationTracker from a serialized state dictionary.

        WHAT
        ====
        Deserialize a previously saved tracker state and reconstruct a fully functional
        AgentReputationTracker instance with identical internal state.

        WHY
        ====
        Enables exact state restoration from persistence layers. Critical for audit trails,
        checkpoint recovery, and cross-process state transfer.

        HOW
        ===
        1. Validate top-level schema (required keys, no extra keys).
        2. Construct a fresh tracker with the serialized agent_ids, regimes, and priors.
        3. Validate each state entry: canonical key format, registered agent/regime,
           non-negative integer observations, parameter bounds, and mathematical invariants.
        4. Enforce closed schema: reject unexpected top-level or per-entry keys.
        5. Enforce absolute error bounds: |Δα - round(Δα)| <= 1e-9 and
           |(Δα + Δβ) - observations| <= 1e-9.
        6. Atomically populate internal state dictionaries after all validation passes.

        Parameters
        ----------
        data : Dict[str, Any]
            Serialized state dictionary from to_dict().

        Returns
        -------
        AgentReputationTracker
            Restored tracker instance with identical state.

        Raises
        ------
        TypeError
            If data is not a dict, or if state entries have wrong types.
        ValueError
            If required keys are missing, extra keys are present, state keys are malformed,
            agents/regimes are unregistered, parameters violate bounds or mathematical invariants,
            or observations are inconsistent with parameter deltas.

        Time Complexity
        ---------------
        O(AR + S) where A = number of agents, R = number of regimes, and S = number of
        state entries in the input dictionary. For valid input, S = AR.

        Space Complexity
        ----------------
        O(AR) auxiliary space for the reconstructed tracker state, where A = number of agents
        and R = number of regimes.

        Cyclomatic Complexity
        ---------------------
        18
        """
        if not isinstance(data, dict):
            raise TypeError(f"data must be a dict, got {type(data).__name__}")

        required_keys = {"agent_ids", "regimes", "prior_alpha", "prior_beta", "state"}
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            raise ValueError(f"Serialized data missing required keys: {sorted(missing_keys)}")

        extra_top_keys = set(data.keys()) - required_keys
        if extra_top_keys:
            raise ValueError(f"Serialized data contains unexpected top-level fields: {sorted(extra_top_keys)}")

        tracker = cls(
            agent_ids=data["agent_ids"],
            regimes=data["regimes"],
            prior_alpha=data["prior_alpha"],
            prior_beta=data["prior_beta"],
        )

        state_map = data.get("state")
        if not isinstance(state_map, dict):
            raise TypeError(f"state must be a dict, got {type(state_map).__name__}")

        expected_cardinality = len(tracker._registered_agents) * len(tracker._registered_regimes)
        if len(state_map) != expected_cardinality:
            raise ValueError(
                f"State map cardinality mismatch: expected {expected_cardinality} entries "
                f"for {len(tracker._registered_agents)} agents x {len(tracker._registered_regimes)} regimes, "
                f"got {len(state_map)}"
            )

        expected_pairs = {
            (aid, r)
            for aid in tracker._registered_agents
            for r in tracker._registered_regimes
        }
        
        seen_pairs = set()

        for key_str, vals in state_map.items():
            if not isinstance(key_str, str) or "|" not in key_str:
                raise ValueError(f"Malformed state key '{key_str}'. Expected format 'agent_id|regime'")

            parts = key_str.split("|")
            if len(parts) != 2:
                raise ValueError(f"Malformed state key '{key_str}'. Expected format 'agent_id|regime'")

            aid = parts[0].strip()
            r = parts[1]  # Do NOT strip regime string r to preserve canonical regime contract

            expected_canonical_key = f"{aid}|{r}"
            if key_str != expected_canonical_key:
                raise ValueError(f"State key '{key_str}' is not in canonical format '{expected_canonical_key}'")

            if aid not in tracker._registered_agents:
                raise ValueError(f"State key contains unregistered agent_id '{aid}'")
            if r not in tracker._registered_regimes:
                raise ValueError(f"State key contains unregistered regime '{r}'")

            key = (aid, r)
            if key in seen_pairs:
                raise ValueError(f"Duplicate/colliding state key entry for pair {key} in state map ('{key_str}')")
            seen_pairs.add(key)

            if not isinstance(vals, dict):
                raise TypeError(f"State entry for '{key_str}' must be a dict, got {type(vals).__name__}")

            expected_entry_keys = {"alpha", "beta", "observations"}
            missing_entry_fields = expected_entry_keys - set(vals.keys())
            if missing_entry_fields:
                raise ValueError(f"State entry for '{key_str}' missing required fields: {sorted(missing_entry_fields)}")

            extra_entry_fields = set(vals.keys()) - expected_entry_keys
            if extra_entry_fields:
                raise ValueError(f"State entry for '{key_str}' contains unexpected fields: {sorted(extra_entry_fields)}")

            raw_alpha = vals["alpha"]
            raw_beta = vals["beta"]
            raw_obs = vals["observations"]

            alpha_val = _validate_float_param(raw_alpha, f"State alpha for '{key_str}'")
            beta_val = _validate_float_param(raw_beta, f"State beta for '{key_str}'")

            if isinstance(raw_obs, bool) or not isinstance(raw_obs, int):
                raise TypeError(f"State observations for '{key_str}' must be an integer, got {type(raw_obs).__name__}")
            if raw_obs < 0:
                raise ValueError(f"State observations for '{key_str}' cannot be negative, got {raw_obs}")

            prior_a = tracker._alpha[key]
            prior_b = tracker._beta[key]

            if alpha_val < prior_a:
                raise ValueError(f"State alpha for '{key_str}' ({alpha_val}) cannot be less than prior_alpha ({prior_a})")
            if beta_val < prior_b:
                raise ValueError(f"State beta for '{key_str}' ({beta_val}) cannot be less than prior_beta ({prior_b})")

            # Mathematical invariant check: alpha_val and beta_val must be integer increments from prior.
            # Uses integer step k to eliminate float representation carry noise at large scale.
            k_alpha = int(round(alpha_val - prior_a))
            k_beta = int(round(beta_val - prior_b))

            if k_alpha < 0 or abs(alpha_val - (prior_a + float(k_alpha))) > max(1e-9, 1e-12 * alpha_val):
                raise ValueError(
                    f"Mathematical invariant breach for '{key_str}': "
                    f"alpha ({alpha_val}) must be an integer step from prior_alpha ({prior_a})"
                )

            if k_beta < 0 or abs(beta_val - (prior_b + float(k_beta))) > max(1e-9, 1e-12 * beta_val):
                raise ValueError(
                    f"Mathematical invariant breach for '{key_str}': "
                    f"beta ({beta_val}) must be an integer step from prior_beta ({prior_b})"
                )

            if k_alpha + k_beta != raw_obs:
                raise ValueError(
                    f"Mathematical invariant breach for '{key_str}': "
                    f"(alpha - prior_alpha) + (beta - prior_beta) = {k_alpha + k_beta} != observations ({raw_obs})"
                )

            tracker._alpha[key] = alpha_val
            tracker._beta[key] = beta_val
            tracker._observations[key] = raw_obs

        missing_pairs = expected_pairs - seen_pairs
        if missing_pairs:
            raise ValueError(f"State map missing entries for registered pairs: {sorted(missing_pairs)}")

        return tracker
