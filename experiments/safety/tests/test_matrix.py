import csv, json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class MatrixTests(unittest.TestCase):
    def test_frozen_matrix(self):
        with (ROOT/'matrix'/'safety-execution-matrix.csv').open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),10)
        self.assertEqual({r['forecast_condition'] for r in rows},{'persistent_negative_bias','missed_peak'})
        self.assertTrue(all(r['safety_enabled']=='true' and r['safety_off_valid_attempt'] for r in rows))
        self.assertEqual(len({r['safety_off_run_id'] for r in rows}),10)

    def test_validation_summary(self):
        result=json.loads((ROOT/'validation'/'validation-summary.json').read_text(encoding='utf-8'))
        self.assertTrue(result['valid'])

if __name__=='__main__': unittest.main()
