"""Unit tests for HMM regime detector interface and stub implementation."""

import unittest
from datetime import datetime

from investment_agent.regimes.hmm_regime_detector import (
    HMMRegimeDetector,
    StubHMMRegimeDetector,
    RegimeProbability,
    get_hmm_detector,
    _load_regime_config,
)


class TestHMMInterface(unittest.TestCase):
    """Test HMMRegimeDetector abstract interface."""

    def test_cannot_instantiate_abstract_class(self):
        """Verify HMMRegimeDetector cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            HMMRegimeDetector()

    def test_stub_implements_interface(self):
        """Verify StubHMMRegimeDetector implements all abstract methods."""
        stub = StubHMMRegimeDetector()
        self.assertTrue(hasattr(stub, "classify"))
        self.assertTrue(hasattr(stub, "update_transition_matrix"))
        self.assertTrue(hasattr(stub, "get_emission_parameters"))


class TestStubHMMRegimeDetector(unittest.TestCase):
    """Test StubHMMRegimeDetector behavior."""

    def test_classify_raises_not_implemented(self):
        """Verify classify() raises NotImplementedError."""
        stub = StubHMMRegimeDetector()
        with self.assertRaises(NotImplementedError):
            stub.classify([50.0, 0.0, 1.0, 20.0, 1.0, 0.5, 0.5])

    def test_update_transition_matrix_raises_not_implemented(self):
        """Verify update_transition_matrix() raises NotImplementedError."""
        stub = StubHMMRegimeDetector()
        with self.assertRaises(NotImplementedError):
            stub.update_transition_matrix([[0.9, 0.1], [0.1, 0.9]])

    def test_get_emission_parameters_raises_not_implemented(self):
        """Verify get_emission_parameters() raises NotImplementedError."""
        stub = StubHMMRegimeDetector()
        with self.assertRaises(NotImplementedError):
            stub.get_emission_parameters("R01")


class TestHMMDetectorFactory(unittest.TestCase):
    """Test get_hmm_detector() factory function."""

    def test_factory_returns_hmm_detector(self):
        """Verify factory returns HMMRegimeDetector instance."""
        detector = get_hmm_detector()
        self.assertIsInstance(detector, HMMRegimeDetector)

    def test_factory_returns_stub_by_default(self):
        """Verify factory returns stub implementation."""
        detector = get_hmm_detector()
        self.assertIsInstance(detector, StubHMMRegimeDetector)


class TestRegimeProbability(unittest.TestCase):
    """Test RegimeProbability dataclass."""

    def test_regime_probability_creation(self):
        """Verify RegimeProbability can be created with valid fields."""
        probs = {f"R{i:02d}": 1.0 / 12 for i in range(1, 13)}
        rp = RegimeProbability(
            regime="R01",
            probabilities=probs,
            entropy=2.0,
            dwell_time=3,
            is_confident=True,
        )
        self.assertEqual(rp.regime, "R01")
        self.assertEqual(rp.dwell_time, 3)
        self.assertTrue(rp.is_confident)


class TestRegimeConfigLoading(unittest.TestCase):
    """Test regime configuration loading."""

    def test_load_regime_config_returns_dict(self):
        """Verify _load_regime_config returns a dictionary."""
        config = _load_regime_config()
        self.assertIsInstance(config, dict)

    def test_regime_config_has_regimes_section(self):
        """Verify loaded config has regimes section if file exists."""
        config = _load_regime_config()
        if config:
            self.assertIn("regimes", config)


if __name__ == "__main__":
    unittest.main()
