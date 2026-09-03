from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from dispatch_observer import DispatchAccumulator

class DispatchObserverTests(unittest.TestCase):
    def test_counts_actual_dispatches(self):
        a=DispatchAccumulator('run-1');[a.note_dispatch(0) for _ in range(25)]
        row=a.finalize(0);self.assertEqual(row.dispatch_count,25);self.assertEqual(row.observed_demand_rps,25)
    def test_zero_dispatch_window_is_explicit(self):
        row=DispatchAccumulator('run-1').finalize(0);self.assertEqual(row.dispatch_count,0)
    def test_rejects_late_dispatch(self):
        a=DispatchAccumulator('run-1');a.finalize(0)
        with self.assertRaises(ValueError):a.note_dispatch(0)
    def test_requires_sequential_finalization(self):
        a=DispatchAccumulator('run-1')
        with self.assertRaises(ValueError):a.finalize(1)

if __name__=='__main__':unittest.main()
