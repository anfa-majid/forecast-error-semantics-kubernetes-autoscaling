import json,re
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
REPOSITORY=ROOT.parents[1]
CONTROLLER=REPOSITORY/'controller'
KUBERNETES=REPOSITORY/'kubernetes'/'controller'

class ControllerContractTests(unittest.TestCase):
    def test_runtime_enables_explicit_safety_only(self):
        runtime=json.loads((CONTROLLER/'configuration'/'runtime-config.example.json').read_text())
        self.assertTrue(runtime['safety_enabled']);self.assertEqual(runtime['safety_policy_path'],'/etc/anfa/safety/safety-policy.json')
    def test_controller_is_separately_versioned(self):
        deployment=(KUBERNETES/'deployment.yaml').read_text()
        self.assertIn('forecast-error-study/predictive-autoscaler:1.1.2',deployment)
        self.assertNotIn('anfa/predictive-autoscaler:1.0.0',deployment)
    def test_single_writer_arbitration_is_wired(self):
        source=(CONTROLLER/'internal'/'controller'/'controller.go').read_text()
        for token in ('decisionMu','UpdatePredictive','UpdateSafetyFloor','applyFinalDecision','ReadyReplicas'):
            self.assertIn(token,source)
    def test_safety_service_and_mount(self):
        service=(KUBERNETES/'safety-service.yaml').read_text()
        deployment=(KUBERNETES/'deployment.yaml').read_text()
        self.assertIn('nodePort: 30081',service);self.assertIn('/etc/anfa/safety',deployment)
    def test_safety_policy_matches_reference(self):
        reference=json.loads((ROOT/'configuration'/'safety-policy.json').read_text())
        controller=json.loads((CONTROLLER/'configuration'/'safety-policy.json').read_text())
        for key in ('policy_id','policy_version','observation_interval_seconds','trigger_persistence_seconds','release_hold_seconds','min_replicas','max_replicas','capacity_lookup'):
            self.assertEqual(controller[key],reference[key])

if __name__=='__main__':unittest.main()
