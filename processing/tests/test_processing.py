import importlib.util,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tools/process_step17.py';spec=importlib.util.spec_from_file_location('processor',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ProcessingTests(unittest.TestCase):
    def test_episodes(self):self.assertEqual(m.episodes([False,True,True,False,True]),[(1,2),(4,4)])
    def test_percentile(self):self.assertEqual(m.percentile([1,2,3,4],.5),2.5)
    def test_actions(self):self.assertEqual(m.action_metrics([1,1,3,2]),(2,3,1,1))
    def test_capacity_boundaries(self):
        self.assertEqual([m.required(x) for x in (30,31,40,41,55,56,65)],[1,2,2,3,3,4,4])
    def test_event_construction(self):
        w=[{'event_label':''},{'event_label':'transition_onset;peak_start'},{'event_label':'cycle_end'},{'event_label':'transition_onset'},{'event_label':'recovery_complete'}]
        self.assertEqual(m.build_events(w),[(1,1,2),(2,3,4)])
if __name__=='__main__':unittest.main()
