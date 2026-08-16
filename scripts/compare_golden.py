"""Compares backtest output artifacts against golden baseline directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_directories(actual_dir: Path, golden_dir: Path) -> int:
    if not actual_dir.exists():
        print(f"Error: Actual directory does not exist: {actual_dir}", file=sys.stderr)
        return 1
    if not golden_dir.exists():
        print(f"Error: Golden directory does not exist: {golden_dir}", file=sys.stderr)
        return 1

    actual_files = {p.relative_to(actual_dir): p for p in actual_dir.rglob("*") if p.is_file()}
    golden_files = {p.relative_to(golden_dir): p for p in golden_dir.rglob("*") if p.is_file()}

    if set(actual_files.keys()) != set(golden_files.keys()):
        missing = set(golden_files.keys()) - set(actual_files.keys())
        extra = set(actual_files.keys()) - set(golden_files.keys())
        print(
            f"Error: File mismatch. Missing in actual: {missing}, Extra in actual: {extra}",
            file=sys.stderr,
        )
        return 1

    mismatches: list[str] = []
    for rel_path in sorted(golden_files.keys()):
        act_p = actual_files[rel_path]
        gld_p = golden_files[rel_path]

        # For JSON files, parse and compare payloads ignoring volatile run-timestamps if present
        if rel_path.suffix == ".json":
            try:
                act_data = json.loads(act_p.read_text(encoding="utf-8"))
                gld_data = json.loads(gld_p.read_text(encoding="utf-8"))
                if act_data != gld_data:
                    mismatches.append(f"{rel_path}: JSON content differs")
            except Exception as e:
                if hash_file(act_p) != hash_file(gld_p):
                    mismatches.append(f"{rel_path}: parse error {e} and hash mismatch")
        else:
            if hash_file(act_p) != hash_file(gld_p):
                mismatches.append(f"{rel_path}: file hash mismatch")

    if mismatches:
        for m in mismatches:
            print(f"Mismatch: {m}", file=sys.stderr)
        return 1

    print("Golden comparison passed: all artifacts match.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare backtest artifacts with golden baseline.")
    parser.add_argument("actual", type=Path, help="Path to latest backtest output directory")
    parser.add_argument("golden", type=Path, help="Path to golden baseline directory")
    args = parser.parse_args()

    return compare_directories(args.actual, args.golden)


if __name__ == "__main__":
    sys.exit(main())
