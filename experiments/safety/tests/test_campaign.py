import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CampaignContractTests(unittest.TestCase):
    def test_manager_is_safety_only(self):
        source=(ROOT/'tools'/'campaign.py').read_text()
        self.assertIn("counts['valid']==10",source);self.assertIn("phase']!='secondary_safety'",source);self.assertIn("safety_enabled']!='true'",source)
    def test_matrix_has_comparators(self):
        import csv
        with (ROOT/'matrix'/'safety-execution-matrix.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
        self.assertTrue(all(r['safety_off_run_id'] and r['safety_off_valid_attempt'] for r in rows))
if __name__=='__main__':unittest.main()
