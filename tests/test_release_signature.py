"""The acceptance record's signature has to detect edits, or it is decoration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from verify_release import sign, verify_release  # noqa: E402

RECORD = {
    "release_id": "quantlab-test",
    "version": "1.0.0",
    "dataset_id": "DATASET-v001",
    "dataset_manifest_hash": "a" * 64,
    "backtest_content_hash": "b" * 64,
    "backtest_sharpe": 1.23,
    "validation_verdict": "RESEARCH_ONLY",
    "ml_champion": "composite",
}


def _write(tmp_path: Path, record: dict[str, object]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_intact_record_verifies(tmp_path: Path) -> None:
    record = dict(RECORD)
    record["content_hash"] = sign(record)
    assert verify_release("cfg", _write(tmp_path, record)) == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("validation_verdict", "PAPER_CANDIDATE"),
        ("backtest_sharpe", 3.5),
        ("ml_champion", "ridge"),
        ("dataset_manifest_hash", "c" * 64),
    ],
)
def test_editing_any_signed_field_is_detected(tmp_path: Path, field: str, value: object) -> None:
    """Signing a hand-listed subset of fields is how a signature stops covering things.

    Every field is hashed, so promoting a verdict or inflating a Sharpe after the fact
    breaks verification.
    """
    record = dict(RECORD)
    record["content_hash"] = sign(record)
    record[field] = value
    assert verify_release("cfg", _write(tmp_path, record)) == 1


def test_record_missing_required_evidence_is_rejected(tmp_path: Path) -> None:
    """A correctly signed but empty record must not pass as verified."""
    record = {"release_id": "x", "version": "1.0.0"}
    record["content_hash"] = sign(record)
    assert verify_release("cfg", _write(tmp_path, record)) == 1


def test_absent_record_is_rejected(tmp_path: Path) -> None:
    assert verify_release("cfg", tmp_path / "nope.json") == 1
