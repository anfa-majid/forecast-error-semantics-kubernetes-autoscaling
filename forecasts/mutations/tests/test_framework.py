import json, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"tools"))
from mutation_framework import Policy, intervals, metrics, mutate, oracle_forecast

class FrameworkTests(unittest.TestCase):
    def policy(self):
        return Policy("p",((1,30),(2,40),(3,55),(4,65)),6,1,1,4,1,1.0,30,1)

    def test_capacity_boundaries(self):
        p=self.policy();self.assertEqual([p.raw(x) for x in (0,30,30.000001,40,40.000001,55,55.000001,65)],[1,1,2,2,3,3,4,4])
        with self.assertRaises(ValueError):p.raw(65.000001)

    def test_scale_down_stabilization_and_step(self):
        rows=self.policy().replay([60]+[25]*32)
        self.assertEqual(rows[0]["commanded_replicas"],4);self.assertEqual(rows[29]["commanded_replicas"],4)
        self.assertEqual([rows[i]["commanded_replicas"] for i in (30,31,32)],[3,2,1])

    def test_oracle_terminal_extension(self):
        targets,values=oracle_forecast([10,20,30],2);self.assertEqual(targets,[2,3,4]);self.assertEqual(values,[30,30,30])

    def test_bias_changes_only_support(self):
        base={i:25.0 for i in range(20)};spec={"id":"x","type":"add_bias","parameters":{"start_s":5,"end_s":9,"bias_rps":10}}
        out,support=mutate(base,spec,0,65);self.assertEqual({i for i in base if out[i]!=base[i]},set(range(5,10)));self.assertEqual(support,set(range(5,10)))

    def test_early_and_late_shift_sign(self):
        base={i:(60.0 if 10<=i<=19 else 25.0) for i in range(30)}
        early,_=mutate(base,{"id":"e","type":"shift_event","parameters":{"event_start_s":10,"event_end_s":19,"shift_s":-3}},0,65)
        late,_=mutate(base,{"id":"l","type":"shift_event","parameters":{"event_start_s":10,"event_end_s":19,"shift_s":3}},0,65)
        self.assertEqual(next(i for i,v in early.items() if v==60),7);self.assertEqual(next(i for i,v in late.items() if v==60),13)

    def test_intervals(self):
        self.assertEqual(intervals([1,2,3,7,8]),[{"start_s":1,"end_s":3},{"start_s":7,"end_s":8}])

    def test_catalog_contains_required_families(self):
        catalog=json.loads((ROOT/"configuration/mutation-catalog.json").read_text())
        self.assertEqual({x["family"] for x in catalog["mutations"]},{"timing","event_presence","direction_bias","duration","shape","location"})
        self.assertEqual(len({x["id"] for x in catalog["mutations"]}),len(catalog["mutations"]))

if __name__=="__main__":unittest.main()
