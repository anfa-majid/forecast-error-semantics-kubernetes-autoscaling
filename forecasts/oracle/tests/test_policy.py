from __future__ import annotations

import sys
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from policy import PolicyConfig, PolicyEngine


def config(**overrides) -> PolicyConfig:
    values = {
        "capacity_lookup_rps": ((1, 30.0), (2, 40.0), (3, 55.0), (4, 65.0)),
        "min_replicas": 1,
        "max_replicas": 4,
        "initial_replicas": 1,
        "safety_factor": 1.0,
        "scale_down_stabilization_s": 30,
        "decision_interval_s": 1,
        "max_scale_down_step": 1,
        "max_scale_up_step": None,
    }
    values.update(overrides)
    return PolicyConfig(**values)


class PolicyTests(unittest.TestCase):
    def test_golden_capacity_vectors(self):
        vectors = json.loads((ROOT / "samples" / "golden-policy-vectors.json").read_text(encoding="utf-8"))
        engine = PolicyEngine(config())
        for vector in vectors["capacity_vectors"]:
            raw, _ = engine.raw_replicas(float(vector["workload_rps"]))
            self.assertEqual(vector["raw_replicas"], raw)

    def test_empirical_boundaries(self):
        engine = PolicyEngine(config(scale_down_stabilization_s=0))
        cases = [(0, 1), (30, 1), (30.000001, 2), (40, 2), (40.000001, 3), (55, 3), (55.000001, 4), (65, 4)]
        for workload, expected in cases:
            raw, _ = engine.raw_replicas(workload)
            self.assertEqual(expected, raw, workload)

    def test_non_linear_lookup_not_ceil_cpod(self):
        engine = PolicyEngine(config())
        raw, _ = engine.raw_replicas(55)
        self.assertEqual(3, raw)

    def test_above_validated_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            PolicyEngine(config()).decide(65.000001)

    def test_scale_up_is_immediate(self):
        decision = PolicyEngine(config()).decide(60)
        self.assertEqual(4, decision.commanded_replicas)
        self.assertEqual("scale_up", decision.action)

    def test_scale_down_is_held_for_thirty_samples(self):
        engine = PolicyEngine(config())
        engine.decide(60)
        for _ in range(29):
            decision = engine.decide(25)
            self.assertEqual(4, decision.commanded_replicas)
        decision = engine.decide(25)
        self.assertEqual(3, decision.commanded_replicas)
        self.assertEqual("scale_down", decision.action)

    def test_scale_down_is_limited_to_one_pod_per_decision(self):
        engine = PolicyEngine(config(scale_down_stabilization_s=0))
        self.assertEqual(4, engine.decide(60).commanded_replicas)
        self.assertEqual(3, engine.decide(25).commanded_replicas)
        self.assertEqual(2, engine.decide(25).commanded_replicas)
        self.assertEqual(1, engine.decide(25).commanded_replicas)

    def test_short_dip_is_absorbed(self):
        engine = PolicyEngine(config())
        engine.decide(60)
        for _ in range(10):
            self.assertEqual(4, engine.decide(25).commanded_replicas)
        self.assertEqual(4, engine.decide(60).commanded_replicas)

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            PolicyEngine(config(min_replicas=4, max_replicas=1))


if __name__ == "__main__":
    unittest.main()
