from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

EXCLUDED = {"SHA256SUMS.csv", "manifests/package-inventory.json"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and str(path.relative_to(root)).replace("\\", "/") not in EXCLUDED
        and "__pycache__" not in path.parts
    )
    rows = [
        {
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        }
        for path in files
    ]
    inventory = {
        "schema_version": "1.0.0",
        "package": "step-12-accuracy-matched-forecasts-v1.0.0",
        "file_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "files": rows,
    }
    inventory_path = root / "manifests/package-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with (root / "SHA256SUMS.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["path", "bytes", "sha256"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"files": len(rows), "bytes": inventory["total_bytes"]}, indent=2))


if __name__ == "__main__":
    main()
