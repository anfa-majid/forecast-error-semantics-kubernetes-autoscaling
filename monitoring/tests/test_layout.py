import tempfile
import unittest
from pathlib import Path

from anfa_observability.layout import DIRECTORIES, RunLayout


class LayoutTests(unittest.TestCase):
    def test_creates_complete_layout_and_refuses_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            layout = RunLayout.create(directory, "narrow-spike-v1", "oracle", "run-001")
            self.assertTrue(all((layout.root / item).is_dir() for item in DIRECTORIES))
            (layout.root / "metadata" / "marker").write_text("x")
            with self.assertRaises(FileExistsError):
                RunLayout.create(directory, "narrow-spike-v1", "oracle", "run-001")

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                RunLayout.create(directory, "../escape", "oracle", "run")


if __name__ == "__main__": unittest.main()
