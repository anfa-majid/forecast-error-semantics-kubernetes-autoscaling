from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'tools'))
from replay_expected_safety import replay

class ExpectedReplayTests(unittest.TestCase):
    def test_expected_signatures(self):
        repository=ROOT.parents[1]
        cases=[
          ('pair-01-direction_bias','sustained-peak-v1','pair-01-direction_bias'),
          ('pair-03-event_presence','narrow-spike-v1','pair-03-event_presence')]
        for pair,workload,pair_id in cases:
            rows=replay(
                ROOT/'configuration'/'safety-policy.json',
                repository/'workloads'/'workloads'/f'{workload}.csv',
                repository/'forecasts'/'matched'/'accepted-pairs'/pair/'post-selection-policy-reference.csv',
                pair_id,
            )
            starts=[r for r in rows if r['event']=='intervention_started']
            self.assertEqual(len(starts),1)
            self.assertEqual(starts[0]['final_commanded_replicas'],4)
            self.assertTrue(starts[0]['intervention_changes_command'])

if __name__=='__main__': unittest.main()
