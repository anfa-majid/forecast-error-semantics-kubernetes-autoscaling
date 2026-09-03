from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DIRECTORIES = (
    "metadata",
    "inputs/rendered-manifests",
    "raw/prometheus",
    "normalized",
    "validation",
    "plots",
)


@dataclass(frozen=True)
class RunLayout:
    root: Path

    @classmethod
    def create(cls, results_root: str | Path, workload_id: str, condition: str, run_id: str) -> "RunLayout":
        for value, label in ((workload_id, "workload_id"), (condition, "condition"), (run_id, "run_id")):
            if not value or any(token in value for token in ("/", "\\", "..")):
                raise ValueError(f"unsafe {label}")
        root = Path(results_root) / workload_id / condition / run_id
        if root.exists() and any(root.iterdir()):
            raise FileExistsError(f"run directory already contains data: {root}")
        for relative in DIRECTORIES:
            (root / relative).mkdir(parents=True, exist_ok=True)
        return cls(root=root)

    def path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if self.root.resolve() not in candidate.parents and candidate != self.root.resolve():
            raise ValueError("path escapes run directory")
        return candidate
