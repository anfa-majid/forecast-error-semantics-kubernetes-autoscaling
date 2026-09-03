import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"tools"))
from matching_framework import rel_diff,semantic_check

class MatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.protocol=json.loads((ROOT/"configuration/matching-protocol.json").read_text())
    def c(self,side,metrics,params=None,support=None):return {"side":side,"metrics":metrics,"parameters":params or {},"support_s":support or []}
    def test_symmetric_relative_difference(self):
        self.assertAlmostEqual(rel_diff(2,2.02),rel_diff(2.02,2));self.assertEqual(rel_diff(0,0),0)
    def test_timing_gate_requires_opposite_meaningful_signs(self):
        a=self.c("early",{"peak_timing_error_s":-10});b=self.c("late",{"peak_timing_error_s":10})
        self.assertTrue(semantic_check("timing_spike",a,b,self.protocol)[0])
        b["metrics"]["peak_timing_error_s"]=-10;self.assertFalse(semantic_check("timing_spike",a,b,self.protocol)[0])
    def test_direction_gate(self):
        a=self.c("negative",{"signed_bias_rps":-5});b=self.c("positive",{"signed_bias_rps":5});self.assertTrue(semantic_check("direction_bias",a,b,self.protocol)[0])
    def test_duration_gate(self):
        a=self.c("shortened",{"duration_error_s":-30});b=self.c("extended",{"duration_error_s":30});self.assertTrue(semantic_check("duration",a,b,self.protocol)[0])
    def test_location_overlap_rejected(self):
        a=self.c("stable",{},support=[1,2]);b=self.c("transition",{},support=[2,3]);self.assertFalse(semantic_check("location",a,b,self.protocol)[0])
    def test_shape_gate(self):
        a=self.c("smoothed",{},params={"radius_s":10});b=self.c("sharpened",{},params={"radius_s":10});self.assertTrue(semantic_check("shape",a,b,self.protocol)[0])
    def test_protocol_forbids_operational_selection(self):
        forbidden=set(self.protocol["forbidden_selection_fields"]);self.assertIn("latency",forbidden);self.assertIn("commanded_replicas",forbidden)
if __name__=="__main__":unittest.main()
