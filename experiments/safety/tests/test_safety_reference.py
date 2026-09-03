import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from safety_reference import SafetyConfig, SafetyEngine

class SafetyReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = SafetyConfig.load(ROOT / "configuration" / "safety-policy.json")

    def test_capacity_boundaries(self):
        cases = [(0,1),(30,1),(30.0001,2),(40,2),(40.0001,3),(55,3),(55.0001,4),(65,4)]
        self.assertEqual([(v,self.config.required_replicas(v)) for v,_ in cases], cases)
        with self.assertRaises(ValueError): self.config.required_replicas(65.1)

    def test_two_windows_required(self):
        engine = SafetyEngine(self.config)
        self.assertFalse(engine.evaluate(60,1,1)["safety_active"])
        second = engine.evaluate(60,1,1)
        self.assertEqual(second["event"], "intervention_started")
        self.assertEqual(second["final_commanded_replicas"], 4)

    def test_never_reduces_predictive_command(self):
        record = SafetyEngine(self.config).evaluate(25,1,4)
        self.assertEqual(record["final_commanded_replicas"], 4)

    def test_missing_is_logged_without_trigger(self):
        record = SafetyEngine(self.config).evaluate(None,1,1)
        self.assertTrue(record["observation_missing"])
        self.assertFalse(record["triggered"])

    def test_release_after_hold(self):
        engine = SafetyEngine(self.config)
        engine.evaluate(60,1,1); engine.evaluate(60,1,1)
        for _ in range(29): self.assertTrue(engine.evaluate(25,4,1)["safety_active"])
        released = engine.evaluate(25,4,1)
        self.assertEqual(released["event"], "intervention_released")

    def test_no_condition_specific_parameters(self):
        raw=json.loads((ROOT/'configuration'/'safety-policy.json').read_text(encoding='utf-8'))
        self.assertFalse(raw['condition_specific_parameters'])

if __name__ == '__main__': unittest.main()
