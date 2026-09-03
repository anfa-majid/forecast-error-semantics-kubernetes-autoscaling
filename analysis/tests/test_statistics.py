import importlib.util, pathlib, unittest
import numpy as np

P=pathlib.Path(__file__).parents[1]/"tools"/"analyze_step18.py"
S=importlib.util.spec_from_file_location("analysis",P); M=importlib.util.module_from_spec(S); S.loader.exec_module(M)

class StatisticalTests(unittest.TestCase):
    def test_exact_resolution_eight(self): self.assertAlmostEqual(M.exact_signflip(np.ones(8)),2/256)
    def test_exact_resolution_five(self): self.assertAlmostEqual(M.exact_signflip(np.ones(5)),2/32)
    def test_null(self): self.assertEqual(M.exact_signflip(np.zeros(8)),1.0)
    def test_rank_biserial(self):
        self.assertEqual(M.rank_biserial(np.ones(5)),1.0)
        self.assertEqual(M.rank_biserial(-np.ones(5)),-1.0)
    def test_holm_monotonic(self):
        got=M.holm([.01,.02,.5]); self.assertTrue(np.allclose(got,[.03,.04,.5]))
    def test_kendall(self):
        self.assertAlmostEqual(M.kendall_tau_b([1,2,3],[1,2,3]),1.0)
        self.assertAlmostEqual(M.kendall_tau_b([1,2,3],[3,2,1]),-1.0)

if __name__=="__main__": unittest.main()
