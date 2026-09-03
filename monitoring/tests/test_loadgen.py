import tempfile
import unittest
from pathlib import Path

from anfa_observability.loadgen import epoch_ns_to_utc, load_schedule


class ScheduleTests(unittest.TestCase):
    def write(self, directory, content):
        path = Path(directory) / "schedule.csv"; path.write_text(content, encoding="utf-8"); return path

    def test_loads_authoritative_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, "request_id,scheduled_offset_us,source_second,target_rps,scheduled_requests_in_second\nreq-1,20000,0,25,25\nreq-2,60000,0,25,25\n")
            rows = load_schedule(path)
            self.assertEqual([r.scheduled_offset_us for r in rows], [20000, 60000])

    def test_rejects_duplicate_ids_and_unordered_offsets(self):
        with tempfile.TemporaryDirectory() as directory:
            duplicate = self.write(directory, "request_id,scheduled_offset_us,source_second,target_rps,scheduled_requests_in_second\na,2,0,1,1\na,3,0,1,1\n")
            with self.assertRaises(ValueError): load_schedule(duplicate)
            unordered = self.write(directory, "request_id,scheduled_offset_us,source_second,target_rps,scheduled_requests_in_second\na,3,0,1,1\nb,2,0,1,1\n")
            with self.assertRaises(ValueError): load_schedule(unordered)

    def test_epoch_ns_summary_timestamp_is_utc(self):
        self.assertEqual(epoch_ns_to_utc(1_700_000_000_123_456_000), "2023-11-14T22:13:20.123456Z")


if __name__ == "__main__": unittest.main()
