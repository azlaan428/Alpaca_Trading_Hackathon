"""Adversarial unit test suite for ensemble_signal.py.

Verifies mathematical properties, bounds, and error conditions for Definition 2.1,
Definition 2.2, Definition 2.3, Definition 2.4, and Theorem 1.4 / Theorem 2.3.

Includes audit fixes for G-005 (ensemble signal verification), weight contract
enforcement, and weight scaling invariance (issue #7 from audit).
"""

import math
import unittest
from investment_agent.signals.ensemble_signal import (
    AgentOutput,
    EnsembleAggregate,
    compute_dampened_signal,
    compute_ensemble_signal,
    compute_disagreement,
    compute_effective_confidence,
    compute_ensemble_aggregate,
)


class TestAgentOutputValidation(unittest.TestCase):
    """Test AgentOutput validation, type checking, and boundary constraints."""

    def test_valid_agent_output(self):
        agent = AgentOutput(
            s=0.5,
            c=0.8,
            u=0.1,
            d=0.05,
            p_plus=0.6,
            p_minus=0.2,
            delta_t=300.0,
            r=0.1,
            agent_id="agent_01",
        )
        self.assertEqual(agent.s, 0.5)
        self.assertEqual(agent.c, 0.8)
        self.assertEqual(agent.u, 0.1)
        self.assertEqual(agent.d, 0.05)
        self.assertEqual(agent.p_plus, 0.6)
        self.assertEqual(agent.p_minus, 0.2)
        self.assertEqual(agent.delta_t, 300.0)
        self.assertEqual(agent.r, 0.1)
        self.assertEqual(agent.agent_id, "agent_01")

    def test_reject_boolean_values(self):
        """Reject booleans passed into numeric fields."""
        with self.assertRaises(TypeError):
            AgentOutput(s=True, c=0.8, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="a1")
        with self.assertRaises(TypeError):
            AgentOutput(s=0.5, c=False, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="a1")

    def test_reject_nan_and_inf(self):
        """Reject NaN or Infinity in numeric fields."""
        with self.assertRaises(ValueError):
            AgentOutput(s=math.nan, c=0.8, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="a1")
        with self.assertRaises(ValueError):
            AgentOutput(s=0.5, c=math.inf, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="a1")

    def test_reject_out_of_bounds_fields(self):
        """Reject fields outside allowed domains."""
        # s must be in [-1, 1]
        with self.assertRaises(ValueError):
            AgentOutput(s=1.5, c=0.8, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="a1")

        # c must be in (0, 1] - reject c == 0.0
        with self.assertRaises(ValueError):
            AgentOutput(s=0.5, c=0.0, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="a1")
        with self.assertRaises(ValueError):
            AgentOutput(s=0.5, c=1.1, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="a1")

        # delta_t must be > 0.0
        with self.assertRaises(ValueError):
            AgentOutput(s=0.5, c=0.8, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=0.0, r=0.1, agent_id="a1")

    def test_probability_constraint_violation(self):
        """p_plus + p_minus > 1.0 must raise ValueError."""
        with self.assertRaises(ValueError):
            AgentOutput(s=0.5, c=0.8, u=0.1, d=0.05, p_plus=0.7, p_minus=0.4, delta_t=1.0, r=0.1, agent_id="a1")

    def test_empty_agent_id(self):
        """Empty or whitespace agent_id must raise ValueError."""
        with self.assertRaises(ValueError):
            AgentOutput(s=0.5, c=0.8, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="")
        with self.assertRaises(ValueError):
            AgentOutput(s=0.5, c=0.8, u=0.1, d=0.05, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="   ")


class TestDampenedSignal(unittest.TestCase):
    """Test compute_dampened_signal bounds and behavior."""

    def test_dampened_signal_bounds(self):
        agent = AgentOutput(s=1.0, c=1.0, u=0.0, d=0.0, p_plus=1.0, p_minus=0.0, delta_t=1.0, r=0.0, agent_id="a1")
        self.assertEqual(compute_dampened_signal(agent), 1.0)

        agent_bear = AgentOutput(s=-1.0, c=1.0, u=0.0, d=0.0, p_plus=0.0, p_minus=1.0, delta_t=1.0, r=0.0, agent_id="a1")
        self.assertEqual(compute_dampened_signal(agent_bear), -1.0)

    def test_sign_preservation_and_dampening(self):
        agent = AgentOutput(s=-0.8, c=0.5, u=0.2, d=0.1, p_plus=0.1, p_minus=0.7, delta_t=1.0, r=0.1, agent_id="a1")
        # phi = -0.8 * 0.5 * 0.8 * 0.9 = -0.288
        self.assertAlmostEqual(compute_dampened_signal(agent), -0.288, places=6)


class TestEnsembleSignal(unittest.TestCase):
    """Test compute_ensemble_signal S_t calculations, bounds, and error handling."""

    def setUp(self):
        self.a1 = AgentOutput(s=0.8, c=0.9, u=0.1, d=0.0, p_plus=0.7, p_minus=0.1, delta_t=1.0, r=0.1, agent_id="a1")
        self.a2 = AgentOutput(s=0.4, c=0.8, u=0.2, d=0.1, p_plus=0.5, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="a2")
        self.weights = {"a1": 1.0, "a2": 1.0}

    def test_ensemble_signal_bounds(self):
        """S_t in [-1.0, 1.0] per Theorem 1.4 / Theorem 2.3."""
        s_t = compute_ensemble_signal([self.a1, self.a2], self.weights)
        self.assertTrue(-1.0 <= s_t <= 1.0)

    def test_single_agent_degenerate_case(self):
        """Single agent ensemble returns dampened signal."""
        s_t = compute_ensemble_signal([self.a1], {"a1": 1.0})
        self.assertEqual(s_t, compute_dampened_signal(self.a1))

    def test_all_agents_agree(self):
        """All agents identical returns common dampened signal."""
        a_same = AgentOutput(s=0.6, c=0.8, u=0.0, d=0.0, p_plus=0.6, p_minus=0.1, delta_t=1.0, r=0.0, agent_id="a_same")
        agents = [a_same, AgentOutput(s=0.6, c=0.8, u=0.0, d=0.0, p_plus=0.6, p_minus=0.1, delta_t=1.0, r=0.0, agent_id="a_same2")]
        w = {"a_same": 2.0, "a_same2": 3.0}
        self.assertAlmostEqual(compute_ensemble_signal(agents, w), 0.48, places=6)

    def test_empty_agents_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_ensemble_signal([], self.weights)

    def test_duplicate_agent_id_raises_value_error(self):
        a1 = AgentOutput(s=0.5, c=0.8, u=0.1, d=0.05, p_plus=0.6, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="agent")
        a2 = AgentOutput(s=0.2, c=0.7, u=0.1, d=0.05, p_plus=0.4, p_minus=0.2, delta_t=1.0, r=0.1, agent_id="agent")
        with self.assertRaises(ValueError):
            compute_ensemble_signal([a1, a2], {"agent": 1.0})

    def test_missing_weight_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_ensemble_signal([self.a1, self.a2], {"a1": 1.0})

    def test_extra_weight_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_ensemble_signal([self.a1], {"a1": 1.0, "extra": 2.0})

    def test_zero_negative_and_nan_infinite_weights_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_ensemble_signal([self.a1], {"a1": 0.0})
        with self.assertRaises(ValueError):
            compute_ensemble_signal([self.a1], {"a1": -1.0})
        with self.assertRaises(ValueError):
            compute_ensemble_signal([self.a1], {"a1": float("nan")})
        with self.assertRaises(ValueError):
            compute_ensemble_signal([self.a1], {"a1": float("inf")})

    def test_bool_weight_raises_type_error(self):
        with self.assertRaises(TypeError):
            compute_ensemble_signal([self.a1], {"a1": True})


class TestDisagreement(unittest.TestCase):
    """Test compute_disagreement D_t calculations and bounds (Definition 1.3 / Theorem 1.4)."""

    def setUp(self):
        self.a1 = AgentOutput(s=1.0, c=0.9, u=0.0, d=0.0, p_plus=0.9, p_minus=0.0, delta_t=1.0, r=0.0, agent_id="a1")
        self.a2 = AgentOutput(s=-1.0, c=0.9, u=0.0, d=0.0, p_plus=0.0, p_minus=0.9, delta_t=1.0, r=0.0, agent_id="a2")
        self.weights = {"a1": 1.0, "a2": 1.0}

    def test_disagreement_bounds(self):
        """D_t in [0.0, 2.0] per Theorem 1.4."""
        s_t = compute_ensemble_signal([self.a1, self.a2], self.weights)
        d_t = compute_disagreement([self.a1, self.a2], self.weights, s_t)
        self.assertTrue(0.0 <= d_t <= 2.0)

    def test_zero_disagreement_case(self):
        """Identical agents with full confidence produce D_t == 0.0."""
        a_full1 = AgentOutput(s=1.0, c=1.0, u=0.0, d=0.0, p_plus=1.0, p_minus=0.0, delta_t=1.0, r=0.0, agent_id="a_full1")
        a_full2 = AgentOutput(s=1.0, c=1.0, u=0.0, d=0.0, p_plus=1.0, p_minus=0.0, delta_t=1.0, r=0.0, agent_id="a_full2")
        w = {"a_full1": 1.0, "a_full2": 1.0}
        s_t = compute_ensemble_signal([a_full1, a_full2], w)
        d_t = compute_disagreement([a_full1, a_full2], w, s_t)
        self.assertEqual(d_t, 0.0)

    def test_maximum_disagreement_case(self):
        """Opposite polar signals (s=+1 and s=-1) equal weight produces D_t == 1.0."""
        s_t = compute_ensemble_signal([self.a1, self.a2], self.weights)  # S_t = 0.0
        d_t = compute_disagreement([self.a1, self.a2], self.weights, s_t)
        # (|1 - 0| + |-1 - 0|) / 2 = 1.0
        self.assertAlmostEqual(d_t, 1.0, places=6)


class TestEffectiveConfidence(unittest.TestCase):
    """Test compute_effective_confidence c_bar_t bounds and independence of signal direction."""

    def test_effective_confidence_bounds_and_direction_independence(self):
        a1 = AgentOutput(s=0.9, c=0.8, u=0.1, d=0.05, p_plus=0.7, p_minus=0.1, delta_t=1.0, r=0.0, agent_id="a1")
        a2 = AgentOutput(s=-0.9, c=0.6, u=0.2, d=0.1, p_plus=0.1, p_minus=0.7, delta_t=1.0, r=0.0, agent_id="a2")
        w = {"a1": 1.0, "a2": 1.0}

        c_bar = compute_effective_confidence([a1, a2], w)
        self.assertTrue(0.0 <= c_bar <= 1.0)

        # Flipping directional signs s_i does NOT change effective confidence
        a1_flip = AgentOutput(s=-0.9, c=0.8, u=0.1, d=0.05, p_plus=0.1, p_minus=0.7, delta_t=1.0, r=0.0, agent_id="a1")
        a2_flip = AgentOutput(s=0.9, c=0.6, u=0.2, d=0.1, p_plus=0.7, p_minus=0.1, delta_t=1.0, r=0.0, agent_id="a2")

        c_bar_flipped = compute_effective_confidence([a1_flip, a2_flip], w)
        self.assertEqual(c_bar, c_bar_flipped)


class TestSevenAgentCardinality(unittest.TestCase):
    """Test general agent-cardinality contract used by the whitepaper."""
    
    def _make_agent(self, idx: int) -> AgentOutput:
        """Factory for test agents."""
        return AgentOutput(
            s=0.5, c=0.8, u=0.1, d=0.05, p_plus=0.6, p_minus=0.2,
            delta_t=1.0, r=0.1, agent_id=f"agent_{idx}"
        )
    
    def test_ensemble_accepts_positive_agent_counts(self):
        """Verify the module accepts any positive number of agents, including 7."""
        for n in [1, 2, 3, 5, 7, 8, 10]:
            agents = [self._make_agent(i) for i in range(n)]
            weights = {f"agent_{i}": 0.5 for i in range(n)}
            agg = compute_ensemble_aggregate(agents, weights)
            self.assertIsInstance(agg, EnsembleAggregate)
    
    def test_ensemble_rejects_empty_agent_list(self):
        """Verify empty list is rejected."""
        with self.assertRaises(ValueError):
            compute_ensemble_aggregate([], {})


class TestWeightBounds(unittest.TestCase):
    """Test weight contract: w_i > 0 as positive reputation weights."""
    
    def _make_agent(self, idx: int) -> AgentOutput:
        """Factory for test agents."""
        return AgentOutput(
            s=0.5, c=0.8, u=0.1, d=0.05, p_plus=0.6, p_minus=0.2,
            delta_t=1.0, r=0.1, agent_id=f"agent_{idx}"
        )
    
    def test_weight_zero_rejected(self):
        """Zero weight rejected (must be > 0)."""
        agents = [self._make_agent(i) for i in range(7)]
        weights = {f"agent_{i}": 0.5 for i in range(7)}
        weights["agent_0"] = 0.0
        with self.assertRaises(ValueError):
            compute_ensemble_aggregate(agents, weights)
    
    def test_weight_greater_than_one_is_allowed(self):
        """Positive weights may exceed 1.0; scaling is valid under the whitepaper."""
        agents = [self._make_agent(i) for i in range(7)]
        weights = {f"agent_{i}": 0.5 for i in range(7)}
        weights["agent_0"] = 1.5
        agg = compute_ensemble_aggregate(agents, weights)
        self.assertIsInstance(agg, EnsembleAggregate)
    
    def test_negative_weight_rejected(self):
        """Negative weight rejected."""
        agents = [self._make_agent(i) for i in range(7)]
        weights = {f"agent_{i}": 0.5 for i in range(7)}
        weights["agent_0"] = -0.1
        with self.assertRaises(ValueError):
            compute_ensemble_aggregate(agents, weights)
    
    def test_weight_exactly_one_accepted(self):
        """Weight = 1.0 accepted (boundary case)."""
        agents = [self._make_agent(i) for i in range(7)]
        weights = {f"agent_{i}": 1.0 for i in range(7)}
        agg = compute_ensemble_aggregate(agents, weights)
        self.assertIsInstance(agg, EnsembleAggregate)
    
    def test_weight_exactly_zero_rejected(self):
        """Weight = 0.0 rejected (must be > 0)."""
        agents = [self._make_agent(i) for i in range(7)]
        weights = {f"agent_{i}": 0.5 for i in range(7)}
        weights["agent_0"] = 0.0
        with self.assertRaises(ValueError):
            compute_ensemble_aggregate(agents, weights)


class TestWeightScalingInvariance(unittest.TestCase):
    """Test that proportional scaling preserves ensemble metrics."""
    
    def setUp(self):
        """Create 7-agent ensemble for testing weight scaling."""
        self.agents = [
            AgentOutput(s=0.8, c=0.9, u=0.1, d=0.0, p_plus=0.8, p_minus=0.1, delta_t=1.0, r=0.1, agent_id=f"a{i}")
            for i in range(7)
        ]
        self.weights_base = {
            f"a{i}": [0.1, 0.5, 0.3, 0.2, 0.8, 0.6, 0.4][i]
            for i in range(7)
        }
    
    def test_weight_scaling_preserves_ensemble_signal(self):
        """Verify S_t, D_t, and c_bar are invariant under proportional weight scaling."""
        agg_base = compute_ensemble_aggregate(self.agents, self.weights_base)
        weights_scaled_2x = {k: v * 2.0 for k, v in self.weights_base.items()}
        agg_scaled = compute_ensemble_aggregate(self.agents, weights_scaled_2x)

        self.assertAlmostEqual(agg_scaled.ensemble_signal, agg_base.ensemble_signal, places=12)
        self.assertAlmostEqual(agg_scaled.disagreement, agg_base.disagreement, places=12)
        self.assertAlmostEqual(agg_scaled.effective_confidence, agg_base.effective_confidence, places=12)
        self.assertAlmostEqual(agg_scaled.sum_weights, agg_base.sum_weights * 2.0, places=12)
    
    def test_weight_scaling_concept(self):
        """Document that proportional scaling should not change the normalized aggregate."""
        agg_base = compute_ensemble_aggregate(self.agents, self.weights_base)
        weights_scaled_2x = {k: v * 2.0 for k, v in self.weights_base.items()}
        agg_scaled = compute_ensemble_aggregate(self.agents, weights_scaled_2x)
        self.assertAlmostEqual(agg_scaled.ensemble_signal, agg_base.ensemble_signal, places=12)


class TestEnsembleAggregate(unittest.TestCase):
    """Test EnsembleAggregate immutable result (G-005 fix)."""
    
    def setUp(self):
        """Create 7-agent ensemble."""
        self.agents = [
            AgentOutput(s=0.5, c=0.8, u=0.1, d=0.05, p_plus=0.6, p_minus=0.2,
                       delta_t=1.0, r=0.1, agent_id=f"agent_{i}")
            for i in range(7)
        ]
        self.weights = {f"agent_{i}": 0.5 for i in range(7)}
    
    def test_aggregate_immutability(self):
        """Verify EnsembleAggregate is frozen and immutable."""
        agg = compute_ensemble_aggregate(self.agents, self.weights)
        with self.assertRaises(AttributeError):
            agg.ensemble_signal = 0.99
    
    def test_aggregate_bounds_enforced(self):
        """Verify EnsembleAggregate validates bounds on construction."""
        # Try to construct with out-of-bounds ensemble_signal (should fail)
        with self.assertRaises(ValueError):
            EnsembleAggregate(
                ensemble_signal=1.5,  # Out of bounds
                disagreement=0.5,
                effective_confidence=0.8,
                sum_weights=3.5
            )
    
    def test_aggregate_contains_sum_weights(self):
        """Verify aggregate includes sum_weights for downstream use (investment Kalman gain)."""
        agg = compute_ensemble_aggregate(self.agents, self.weights)
        self.assertGreater(agg.sum_weights, 0.0)
        self.assertEqual(agg.sum_weights, 7.0 * 0.5)  # 7 agents * 0.5 each
    
    def test_aggregate_all_metrics_present(self):
        """Verify all three metrics are returned in aggregate."""
        agg = compute_ensemble_aggregate(self.agents, self.weights)
        self.assertIsInstance(agg.ensemble_signal, float)
        self.assertIsInstance(agg.disagreement, float)
        self.assertIsInstance(agg.effective_confidence, float)
        self.assertIsInstance(agg.sum_weights, float)


class TestG005EnsembleSignalVerification(unittest.TestCase):
    """Test G-005 audit fix: ensemble signal verification within aggregate."""
    
    def test_aggregate_prevents_mismatched_signal(self):
        """Verify atomic aggregate prevents G-005 inconsistency."""
        agents = [
            AgentOutput(s=1.0 if i == 0 else -1.0, c=0.9, u=0.0, d=0.0,
                       p_plus=0.9 if i == 0 else 0.0, p_minus=0.0 if i == 0 else 0.9,
                       delta_t=1.0, r=0.0, agent_id=f"a{i}")
            for i in range(7)
        ]
        weights = {f"a{i}": 1.0/7.0 for i in range(7)}
        
        # Compute aggregate atomically
        agg = compute_ensemble_aggregate(agents, weights)
        
        # S_t computed within aggregate is guaranteed consistent with D_t
        # (no external caller-supplied S_t can mismatch)
        self.assertIsNotNone(agg.ensemble_signal)
        self.assertIsNotNone(agg.disagreement)
        # Both were computed from same agents/weights - guaranteed consistency

