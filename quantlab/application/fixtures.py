from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FixtureIntegrityReport:
    path: str
    status: str
    file_count: int
    row_counts: dict[str, int]
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "status": self.status,
            "file_count": self.file_count,
            "row_counts": self.row_counts,
            "errors": list(self.errors),
        }


def verify_fixture(fixture_path: Path | str) -> FixtureIntegrityReport:
    root = Path(fixture_path).resolve()
    errors: list[str] = []
    row_counts: dict[str, int] = {}

    if not root.is_dir():
        return FixtureIntegrityReport(
            path=str(fixture_path),
            status="FAIL",
            file_count=0,
            row_counts={},
            errors=(f"Directory not found: {fixture_path}",),
        )

    manifest_file = root / "manifest.json"
    if not manifest_file.is_file():
        return FixtureIntegrityReport(
            path=str(fixture_path),
            status="FAIL",
            file_count=0,
            row_counts={},
            errors=("Missing manifest.json",),
        )

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as err:
        return FixtureIntegrityReport(
            path=str(fixture_path),
            status="FAIL",
            file_count=0,
            row_counts={},
            errors=(f"Invalid manifest.json: {err}",),
        )

    source_files = manifest.get("source_files", {})
    source_dir = root / "source"

    for filename, meta in sorted(source_files.items()):
        file_path = source_dir / filename
        if not file_path.is_file():
            errors.append(f"Missing source file: {filename}")
            continue

        content = file_path.read_bytes()
        actual_sha = hashlib.sha256(content).hexdigest()
        expected_sha = meta.get("sha256")
        if actual_sha != expected_sha:
            errors.append(
                f"Checksum mismatch for {filename}: expected {expected_sha}, got {actual_sha}"
            )

        lines = file_path.read_text(encoding="utf-8").strip().splitlines()
        actual_rows = len(lines) - 1 if len(lines) > 0 else 0
        expected_rows = meta.get("row_count")
        if actual_rows != expected_rows:
            errors.append(
                f"Row count mismatch for {filename}: expected {expected_rows}, got {actual_rows}"
            )

        row_counts[filename] = actual_rows

    status = "PASS" if not errors else "FAIL"
    return FixtureIntegrityReport(
        path=str(fixture_path),
        status=status,
        file_count=len(source_files),
        row_counts=row_counts,
        errors=tuple(errors),
    )
