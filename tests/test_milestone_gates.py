"""Behavioral integrity checks for enforceable milestone gates."""

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
    status: str
    dirty: bool
    exit_codes: tuple[int, ...]
    prior_gates: tuple[str, ...]


class GateVerifier(Protocol):
    def verify_milestone(
        self,
        milestone: str,
        require_prior: bool,
        *,
        repository_root: Path,
        _test_policy: dict[str, object] | None = None,
    ) -> GateReportLike: ...


@pytest.fixture
def gate_module() -> GateVerifier:
    specification = importlib.util.spec_from_file_location("verify_milestone", VERIFIER_PATH)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return cast(GateVerifier, module)


def git(root: Path, *arguments: str | Path) -> None:
    subprocess.run(["git", *(str(argument) for argument in arguments)], cwd=root, check=True)


def write_config(root: Path, commands: dict[str, list[list[str]]] | None = None) -> None:
    command = [sys.executable, "-c", "raise SystemExit(0)"]
    configured = commands or {}
    milestones: dict[str, object] = {}
    for number in range(5):
        milestone = f"M{number}"
        protected = ["requirements.lock"]
        if milestone == "M3":
            protected.append("artifacts/golden/synthetic_v1/backtest")
        milestones[milestone] = {
            "commands": configured.get(milestone, [command]),
            "evidence_paths": ["evidence.json"],
            "fixture_ids": ["synthetic-v1"],
            "protected_paths": protected,
            "verification_command": (
                f"python scripts/verify_milestone.py {milestone} --require-prior"
            ),
        }
    (root / "configs").mkdir(exist_ok=True)
    (root / "configs" / "milestones.yaml").write_text(
        json.dumps({"milestones": milestones}), encoding="utf-8"
    )


def initialize_repository(root: Path, *, evidence: bool = True) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "QuantLab Test")
    (root / "requirements.lock").write_text("locked==1.0\n", encoding="utf-8")
    if evidence:
        (root / "evidence.json").write_text('{"fixture":"synthetic-v1"}\n', encoding="utf-8")
    golden = root / "artifacts" / "golden" / "synthetic_v1" / "backtest"
    golden.mkdir(parents=True)
    (golden / "manifest.json").write_text('{"golden":1}\n', encoding="utf-8")
    write_config(root)
    git(root, "add", ".")
    git(root, "commit", "-qm", "initial inputs")


def receipt_path(root: Path, milestone: str) -> Path:
    return root / "artifacts" / "milestone-gates" / f"{milestone}.json"


def transcript_path(root: Path, milestone: str) -> Path:
    return root / "artifacts" / "milestone-gates" / f"{milestone}.transcript.json"


def verify_gate(
    root: Path, gate_module: GateVerifier, milestone: str, require_prior: bool
) -> GateReportLike:
    """Invoke the private test seam with the exact temporary-repository policy."""
    policy = json.loads((root / "configs" / "milestones.yaml").read_text(encoding="utf-8"))
    return gate_module.verify_milestone(
        milestone, require_prior, repository_root=root, _test_policy=policy
    )


def accept_gate(root: Path, gate_module: GateVerifier, milestone: str) -> None:
    report = verify_gate(root, gate_module, milestone, milestone != "M0")
    assert report.status == "PASS", report.prior_gates
    git(root, "add", receipt_path(root, milestone), transcript_path(root, milestone))
    git(root, "commit", "-qm", f"chore(gate): accept {milestone}")


def test_gate_rejects_missing_prior(tmp_path: Path, gate_module: GateVerifier) -> None:
    """Deleting M0 acceptance must prevent M1 acceptance."""
    initialize_repository(tmp_path)
    report = verify_gate(tmp_path, gate_module, "M1", True)
    assert report.status == "REJECTED"
    assert report.prior_gates == ("M0:missing",)


def test_gate_rejects_dirty_tree(tmp_path: Path, gate_module: GateVerifier) -> None:
    """An uncommitted input mutation cannot produce a PASS receipt."""
    initialize_repository(tmp_path)
    (tmp_path / "evidence.json").write_text('{"fixture":"changed"}\n', encoding="utf-8")
    report = verify_gate(tmp_path, gate_module, "M0", False)
    assert report.status == "REJECTED"
    assert report.dirty is True
    assert not receipt_path(tmp_path, "M0").exists()


def test_gate_rejects_failed_command(tmp_path: Path, gate_module: GateVerifier) -> None:
    """A real nonzero subprocess cannot produce a PASS receipt."""
    initialize_repository(tmp_path)
    write_config(tmp_path, {"M0": [[sys.executable, "-c", "raise SystemExit(7)"]]})
    git(tmp_path, "add", "configs/milestones.yaml")
    git(tmp_path, "commit", "-qm", "configure failing gate")
    report = verify_gate(tmp_path, gate_module, "M0", False)
    assert report.status == "REJECTED"
    assert report.exit_codes == (7,)


def test_gate_hashes_evidence(tmp_path: Path, gate_module: GateVerifier) -> None:
    """A committed, unchanged M0 receipt authorizes the next gate."""
    initialize_repository(tmp_path)
    accept_gate(tmp_path, gate_module, "M0")
    report = verify_gate(tmp_path, gate_module, "M1", True)
    assert report.status == "PASS", report.prior_gates
    assert report.prior_gates == ("M0:PASS",)
    receipt = json.loads(receipt_path(tmp_path, "M1").read_text(encoding="utf-8"))
    assert receipt["config_hash"] and receipt["evidence_hashes"]["evidence.json"]


@pytest.mark.parametrize("corruption", ["not_pass", "malformed", "forged", "modified"])
def test_gate_rejects_inauthentic_prior_receipts(
    tmp_path: Path, gate_module: GateVerifier, corruption: str
) -> None:
    """Receipt tampering must not be accepted merely because JSON exists."""
    initialize_repository(tmp_path)
    accept_gate(tmp_path, gate_module, "M0")
    path = receipt_path(tmp_path, "M0")
    if corruption == "malformed":
        path.write_text("not json", encoding="utf-8")
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if corruption == "not_pass":
            payload["status"] = "REJECTED"
        if corruption == "forged":
            payload["git_sha"] = "0" * 40
        path.write_text(json.dumps(payload), encoding="utf-8")
    if corruption == "modified":
        git(tmp_path, "add", path)
        git(tmp_path, "commit", "-qm", "tamper receipt")
    report = verify_gate(tmp_path, gate_module, "M1", True)
    assert report.status == "REJECTED"
    assert not receipt_path(tmp_path, "M1").exists()


def test_gate_rejects_false_prior_requirement_for_later_milestone(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """Passing false for M1 must not bypass its required M0 gate."""
    initialize_repository(tmp_path)
    accept_gate(tmp_path, gate_module, "M0")
    assert verify_gate(tmp_path, gate_module, "M1", False).status == "REJECTED"


def test_gate_rejects_unsafe_config_and_receipt_paths(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """External configuration and receipt symlink escapes must be rejected."""
    initialize_repository(tmp_path)
    external = tmp_path.parent / "outside.yaml"
    external.write_text("{}", encoding="utf-8")
    (tmp_path / "configs" / "milestones.yaml").unlink()
    (tmp_path / "configs" / "milestones.yaml").symlink_to(external)
    with pytest.raises(ValueError):
        gate_module.verify_milestone("M0", False, repository_root=tmp_path)
    (tmp_path / "configs" / "milestones.yaml").unlink()
    write_config(tmp_path)
    gate_directory = tmp_path / "artifacts" / "milestone-gates"
    gate_directory.parent.mkdir(exist_ok=True)
    gate_directory.symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        verify_gate(tmp_path, gate_module, "M0", False)


def test_gate_rejects_command_time_input_mutation(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """A command that changes a protected tracked input cannot receive PASS."""
    initialize_repository(tmp_path)
    code = "from pathlib import Path; Path('requirements.lock').write_text('changed\\n')"
    write_config(tmp_path, {"M0": [[sys.executable, "-c", code]]})
    git(tmp_path, "add", "configs/milestones.yaml")
    git(tmp_path, "commit", "-qm", "configure mutating gate")
    assert verify_gate(tmp_path, gate_module, "M0", False).status == "REJECTED"


def test_gate_rejects_command_time_config_mutation(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """A command that changes the configured policy cannot receive PASS."""
    initialize_repository(tmp_path)
    code = "from pathlib import Path; Path('configs/milestones.yaml').write_text('{}')"
    write_config(tmp_path, {"M0": [[sys.executable, "-c", code]]})
    git(tmp_path, "add", "configs/milestones.yaml")
    git(tmp_path, "commit", "-qm", "configure policy mutator")

    assert verify_gate(tmp_path, gate_module, "M0", False).status == "REJECTED"


def test_gate_hashes_evidence_created_by_command(tmp_path: Path, gate_module: GateVerifier) -> None:
    """Output evidence may be created by a passing command and is hashed afterwards."""
    initialize_repository(tmp_path, evidence=False)
    code = "from pathlib import Path; Path('evidence.json').write_text('{\\\"made\\\":true}\\n')"
    write_config(tmp_path, {"M0": [[sys.executable, "-c", code]]})
    git(tmp_path, "add", "configs/milestones.yaml")
    git(tmp_path, "commit", "-qm", "configure evidence writer")
    report = verify_gate(tmp_path, gate_module, "M0", False)
    assert report.status == "PASS"
    assert json.loads(receipt_path(tmp_path, "M0").read_text())["evidence_hashes"]


def test_gate_rejects_changed_golden_directory(tmp_path: Path, gate_module: GateVerifier) -> None:
    """Changing committed M3 golden inputs invalidates its prior acceptance."""
    initialize_repository(tmp_path)
    for milestone in ("M0", "M1", "M2", "M3"):
        accept_gate(tmp_path, gate_module, milestone)
    golden = tmp_path / "artifacts" / "golden" / "synthetic_v1" / "backtest" / "manifest.json"
    golden.write_text('{"golden":2}\n', encoding="utf-8")
    git(tmp_path, "add", golden)
    git(tmp_path, "commit", "-qm", "change golden")
    report = verify_gate(tmp_path, gate_module, "M4", True)
    assert report.status == "REJECTED"
    assert "M3:hash_changed" in report.prior_gates


def test_gate_rejects_hand_authored_receipt_even_when_fields_match(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """Replaying a valid receipt without its execution transcript is not acceptance."""
    initialize_repository(tmp_path)
    report = verify_gate(tmp_path, gate_module, "M0", False)
    payload = receipt_path(tmp_path, "M0").read_text(encoding="utf-8")
    receipt_path(tmp_path, "M0").unlink()
    transcript_path(tmp_path, "M0").unlink()
    receipt_path(tmp_path, "M0").parent.mkdir(parents=True, exist_ok=True)
    receipt_path(tmp_path, "M0").write_text(payload, encoding="utf-8")
    git(tmp_path, "add", receipt_path(tmp_path, "M0"))
    git(tmp_path, "commit", "-qm", "chore(gate): accept M0")

    next_report = verify_gate(tmp_path, gate_module, "M1", True)

    assert report.status == "PASS"
    assert next_report.status == "REJECTED"
    assert next_report.prior_gates == ("M0:missing_transcript",)


def test_gate_allows_latest_reacceptance_commit(tmp_path: Path, gate_module: GateVerifier) -> None:
    """A later valid acceptance supersedes, rather than invalidates, the first receipt."""
    initialize_repository(tmp_path)
    accept_gate(tmp_path, gate_module, "M0")
    report = verify_gate(tmp_path, gate_module, "M0", False)
    assert report.status == "PASS"
    git(tmp_path, "add", receipt_path(tmp_path, "M0"), transcript_path(tmp_path, "M0"))
    git(tmp_path, "commit", "-qm", "chore(gate): accept M0")

    next_report = verify_gate(tmp_path, gate_module, "M1", True)

    assert next_report.status == "PASS"
    assert next_report.prior_gates == ("M0:PASS",)


@pytest.mark.parametrize("field", ["commands", "evidence_paths", "protected_paths"])
def test_gate_rejects_weakened_canonical_policy(
    tmp_path: Path, gate_module: GateVerifier, field: str
) -> None:
    """Empty canonical requirements cannot silently weaken a production gate."""
    initialize_repository(tmp_path)
    payload = json.loads((tmp_path / "configs" / "milestones.yaml").read_text(encoding="utf-8"))
    payload["milestones"]["M0"][field] = []
    (tmp_path / "configs" / "milestones.yaml").write_text(json.dumps(payload), encoding="utf-8")
    git(tmp_path, "add", "configs/milestones.yaml")
    git(tmp_path, "commit", "-qm", "weaken policy")

    with pytest.raises(ValueError, match="canonical"):
        gate_module.verify_milestone("M0", False, repository_root=tmp_path)


def test_gate_rejects_omitted_canonical_policy_requirement(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """Omitting a canonical requirement cannot silently authorize a gate."""
    initialize_repository(tmp_path)
    payload = json.loads((tmp_path / "configs" / "milestones.yaml").read_text(encoding="utf-8"))
    del payload["milestones"]["M3"]["protected_paths"]
    (tmp_path / "configs" / "milestones.yaml").write_text(json.dumps(payload), encoding="utf-8")
    git(tmp_path, "add", "configs/milestones.yaml")
    git(tmp_path, "commit", "-qm", "omit golden policy")

    with pytest.raises(ValueError, match="canonical"):
        gate_module.verify_milestone("M3", True, repository_root=tmp_path)


def test_gate_rejects_reordered_canonical_policy(tmp_path: Path, gate_module: GateVerifier) -> None:
    """Canonical M0-to-M9 ordering is part of the production trust root."""
    initialize_repository(tmp_path)
    payload = json.loads((tmp_path / "configs" / "milestones.yaml").read_text(encoding="utf-8"))
    milestones = payload["milestones"]
    payload["milestones"] = {"M1": milestones["M1"], "M0": milestones["M0"], **milestones}
    (tmp_path / "configs" / "milestones.yaml").write_text(json.dumps(payload), encoding="utf-8")
    git(tmp_path, "add", "configs/milestones.yaml")
    git(tmp_path, "commit", "-qm", "reorder policy")

    with pytest.raises(ValueError, match="canonical"):
        gate_module.verify_milestone("M0", False, repository_root=tmp_path)


def test_gate_rejects_broken_receipt_symlink_before_resolve(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """A dangling receipt symlink is rejected as a symlink, not merely a missing file."""
    initialize_repository(tmp_path)
    path = receipt_path(tmp_path, "M0")
    path.parent.mkdir(parents=True)
    path.symlink_to("not-there.json")

    with pytest.raises(ValueError, match="symlink"):
        verify_gate(tmp_path, gate_module, "M0", False)


def test_gate_rejects_internal_evidence_symlink_before_hashing(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """An internal symlink is unsafe even when its target remains inside the repository."""
    initialize_repository(tmp_path)
    target = tmp_path / "evidence-target.json"
    target.write_text('{"fixture":"synthetic-v1"}\n', encoding="utf-8")
    (tmp_path / "evidence.json").unlink()
    (tmp_path / "evidence.json").symlink_to(target.name)

    with pytest.raises(ValueError, match="symlink"):
        verify_gate(tmp_path, gate_module, "M0", False)


def test_gate_rejects_wrong_acceptance_provenance(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """Receipt and transcript blobs need the required ancestor acceptance commit identity."""
    initialize_repository(tmp_path)
    report = verify_gate(tmp_path, gate_module, "M0", False)
    assert report.status == "PASS"
    git(tmp_path, "add", receipt_path(tmp_path, "M0"), transcript_path(tmp_path, "M0"))
    git(tmp_path, "commit", "-qm", "pretend gate acceptance")

    next_report = verify_gate(tmp_path, gate_module, "M1", True)

    assert next_report.status == "REJECTED"
    assert next_report.prior_gates == ("M0:invalid_acceptance_commit",)


def test_gate_rejects_committed_evidence_change_after_acceptance(
    tmp_path: Path, gate_module: GateVerifier
) -> None:
    """Changing accepted evidence invalidates the dependent receipt."""
    initialize_repository(tmp_path)
    accept_gate(tmp_path, gate_module, "M0")
    (tmp_path / "evidence.json").write_text('{"fixture":"changed"}\n', encoding="utf-8")
    git(tmp_path, "add", "evidence.json")
    git(tmp_path, "commit", "-qm", "change evidence")

    report = verify_gate(tmp_path, gate_module, "M1", True)

    assert report.status == "REJECTED"
    assert report.prior_gates == ("M0:hash_changed",)


def test_gate_rejects_mutation_after_candidate_receipt_write(
    tmp_path: Path, gate_module: GateVerifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A protected input changed after candidate creation prevents publication."""
    initialize_repository(tmp_path)
    original_write_text = Path.write_text

    def delayed_mutation(
        path: Path,
        data: str,
        *,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        result = original_write_text(path, data, encoding=encoding, errors=errors, newline=newline)
        if path.name == "M0.tmp":
            (tmp_path / "requirements.lock").write_text("late mutation\\n", encoding="utf-8")
        return result

    monkeypatch.setattr(Path, "write_text", delayed_mutation)

    report = verify_gate(tmp_path, gate_module, "M0", False)

    assert report.status == "REJECTED"
    assert not receipt_path(tmp_path, "M0").exists()
