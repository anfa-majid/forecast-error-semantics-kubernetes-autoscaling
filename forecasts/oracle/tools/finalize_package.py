from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def digest(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


excluded = {ROOT / "SHA256SUMS.csv", ROOT / "validation" / "validation-summary.json"}
paths = sorted(
    path
    for path in ROOT.rglob("*")
    if path.is_file()
    and path not in excluded
    and "__pycache__" not in path.parts
    and path.suffix.lower() != ".pyc"
)
with (ROOT / "SHA256SUMS.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["sha256", "path"])
    writer.writeheader()
    for path in paths:
        writer.writerow({"sha256": digest(path), "path": str(path.relative_to(ROOT)).replace("\\", "/")})
print(f"Wrote checksums for {len(paths)} files")
