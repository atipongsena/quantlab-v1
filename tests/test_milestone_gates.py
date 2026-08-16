"""Behavioral checks for enforceable milestone gates."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Protocol, cast

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = PROJECT_ROOT / "scripts" / "verify_milestone.py"


class GateReportLike(Protocol):
    """The public receipt fields exercised by these behavior tests."""

    status: str
    dirty: bool
    exit_codes: tuple[int, ...]
    prior_gates: tuple[str, ...]


class GateVerifier(Protocol):
    """Application boundary used to inject a temporary Git repository."""

    def verify_milestone(
        self,
        milestone: str,
        require_prior: bool,
        *,
        repository_root: Path,
        config_path: Path,
    ) -> GateReportLike: ...


@pytest.fixture
def gate_module() -> GateVerifier:
    """Load the verifier as an importable application boundary."""
    specification = importlib.util.spec_from_file_location("verify_milestone", VERIFIER_PATH)
    assert specification is not None
    assert specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return cast(GateVerifier, module)


def initialize_repository(root: Path) -> None:
    """Create a small real Git repository for a gate test."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "QuantLab Test"], cwd=root, check=True)
    (root / "requirements.lock").write_text("locked==1.0\n", encoding="utf-8")
    (root / "evidence.json").write_text('{"fixture":"synthetic-v1"}\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial evidence"], cwd=root, check=True)


def write_config(root: Path, command: list[str]) -> Path:
    """Write JSON syntax, which is valid YAML, to avoid a parser dependency."""
    config = {
        "milestones": {
            "M0": {
                "commands": [command],
                "evidence_paths": ["evidence.json"],
                "fixture_ids": ["synthetic-v1"],
                "protected_paths": ["requirements.lock"],
                "verification_command": "python scripts/verify_milestone.py M0 --require-prior",
            },
            "M1": {
                "commands": [[sys.executable, "-c", "raise SystemExit(0)"]],
                "evidence_paths": ["evidence.json"],
                "fixture_ids": ["synthetic-v1"],
                "protected_paths": ["requirements.lock"],
                "verification_command": "python scripts/verify_milestone.py M1 --require-prior",
            },
        }
    }
    config_path = root / "milestones.yaml"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    subprocess.run(["git", "add", "milestones.yaml"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "add gate config"], cwd=root, check=True)
    return config_path


def test_gate_rejects_missing_prior(tmp_path: Path, gate_module: GateVerifier) -> None:
    """Removing a required M0 receipt must prevent M1 acceptance."""
    initialize_repository(tmp_path)
    config_path = write_config(tmp_path, [sys.executable, "-c", "raise SystemExit(0)"])

    report = gate_module.verify_milestone(
        "M1", True, repository_root=tmp_path, config_path=config_path
    )

    assert report.status == "REJECTED"
    assert report.prior_gates == ("M0:missing",)
    assert not (tmp_path / "artifacts" / "milestone-gates" / "M1.json").exists()


def test_gate_rejects_dirty_tree(tmp_path: Path, gate_module: GateVerifier) -> None:
    """Removing the start-of-run dirty check would write an invalid PASS receipt."""
    initialize_repository(tmp_path)
    config_path = write_config(tmp_path, [sys.executable, "-c", "raise SystemExit(0)"])
    (tmp_path / "evidence.json").write_text('{"fixture":"changed"}\n', encoding="utf-8")

    report = gate_module.verify_milestone(
        "M0", False, repository_root=tmp_path, config_path=config_path
    )

    assert report.status == "REJECTED"
    assert report.dirty is True
    assert not (tmp_path / "artifacts" / "milestone-gates" / "M0.json").exists()


def test_gate_rejects_failed_command(tmp_path: Path, gate_module: GateVerifier) -> None:
    """Turning a nonzero quality command into PASS would falsely accept a milestone."""
    initialize_repository(tmp_path)
    config_path = write_config(tmp_path, [sys.executable, "-c", "raise SystemExit(7)"])

    report = gate_module.verify_milestone(
        "M0", False, repository_root=tmp_path, config_path=config_path
    )

    assert report.status == "REJECTED"
    assert report.exit_codes == (7,)
    assert not (tmp_path / "artifacts" / "milestone-gates" / "M0.json").exists()


def test_gate_hashes_evidence(tmp_path: Path, gate_module: GateVerifier) -> None:
    """Removing evidence hashing would let later work reuse altered proof."""
    initialize_repository(tmp_path)
    config_path = write_config(tmp_path, [sys.executable, "-c", "raise SystemExit(0)"])

    report = gate_module.verify_milestone(
        "M0", False, repository_root=tmp_path, config_path=config_path
    )

    receipt = json.loads((tmp_path / "artifacts" / "milestone-gates" / "M0.json").read_text())
    assert report.status == "PASS"
    assert report.dirty is False
    assert receipt["evidence_hashes"] == {
        "evidence.json": "634be26fe1bc492efece8e8c268b545d9464f3f6772aac2ea62ee9190514b381"
    }
    expected_lock_hash = "00133cc01004c6ca9720b25e3ac5a667116d605c0b366d79dbee42f8dfc7e83d"
    assert receipt["dependency_lock_hash"] == expected_lock_hash
    assert receipt["protected_file_hashes"] == {"requirements.lock": expected_lock_hash}

    subsequent_report = gate_module.verify_milestone(
        "M1", True, repository_root=tmp_path, config_path=config_path
    )
    assert subsequent_report.status == "PASS"
    assert subsequent_report.prior_gates == ("M0:PASS",)
