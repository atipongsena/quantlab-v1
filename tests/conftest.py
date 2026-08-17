"""Project-wide pytest configuration."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

pytest_plugins = ("tests.socket_guard",)


@pytest.fixture(scope="session", autouse=True)
def preserve_artifacts_state() -> Generator[None, None, None]:
    root = Path(__file__).parent.parent
    tracked = [
        root / "artifacts/datasets/DATASET-v001/manifest.json",
        root / "artifacts/latest/research-report.json",
        root / "artifacts/latest/validation-report.json",
        root / "artifacts/latest/paper-forward-evidence.json",
    ]
    snapshots = {p: p.read_bytes() for p in tracked if p.is_file()}
    yield
    for p, content in snapshots.items():
        p.write_bytes(content)
    if (root / "artifacts/latest").is_dir():
        for temp_p in (root / "artifacts/latest").glob("paper-*.json"):
            if temp_p.name != "paper-forward-evidence.json":
                temp_p.unlink(missing_ok=True)
