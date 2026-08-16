"""Verify and record deterministic, enforceable QuantLab milestone gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

MILESTONES = tuple(f"M{number}" for number in range(10))
PASS = "PASS"
REJECTED = "REJECTED"
type Command = str | Sequence[str]
type CommandRunner = Callable[[Command, Path], int]


@dataclass(frozen=True, slots=True)
class GateReport:
    """Immutable, domain-neutral receipt for one milestone verification."""

    status: str
    commands: tuple[str, ...]
    exit_codes: tuple[int, ...]
    git_sha: str
    dirty: bool
    dependency_lock_hash: str
    protected_file_hashes: dict[str, str]
    artifact_hashes: dict[str, str]
    evidence_hashes: dict[str, str]
    prior_gates: tuple[str, ...]
    fixture_ids: tuple[str, ...]
    reason: str | None = None


def _repository_root(repository_root: Path | None) -> Path:
    return (repository_root or Path.cwd()).resolve()


def _safe_path(root: Path, value: object) -> Path:
    if not isinstance(value, str):
        raise ValueError("configured paths must be strings")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or value == "":
        raise ValueError(f"unsafe repository-relative path: {value!r}")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"path escapes repository: {value!r}") from error
    return candidate


def _hash_file(root: Path, value: object) -> tuple[str, str]:
    path = _safe_path(root, value)
    if not path.is_file():
        raise ValueError(f"required evidence file is missing: {value}")
    return path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_paths(root: Path, values: object) -> dict[str, str]:
    if not isinstance(values, list):
        raise ValueError("configured path lists must be lists")
    return dict(sorted(_hash_file(root, value) for value in values))


def _load_config(config_path: Path, milestone: str) -> Mapping[str, object]:
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid milestone configuration: {config_path}") from error
    milestones = payload.get("milestones") if isinstance(payload, dict) else None
    if not isinstance(milestones, dict) or milestone not in milestones:
        raise ValueError(f"milestone is not configured: {milestone}")
    config = milestones[milestone]
    if not isinstance(config, dict):
        raise ValueError(f"invalid configuration for {milestone}")
    required = ("commands", "evidence_paths", "fixture_ids", "protected_paths")
    if any(key not in config for key in required):
        raise ValueError(f"incomplete configuration for {milestone}")
    return config


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, check=False, text=True
    )


def _git_sha(root: Path) -> str:
    completed = _git(root, "rev-parse", "HEAD")
    if completed.returncode != 0:
        raise ValueError("milestone verification requires a Git commit")
    return completed.stdout.strip()


def _is_dirty_at_start(root: Path) -> bool:
    completed = _git(root, "status", "--porcelain", "--untracked-files=all")
    if completed.returncode != 0:
        raise ValueError("milestone verification requires a Git worktree")
    changes = [line[3:] for line in completed.stdout.splitlines() if len(line) >= 4]
    return any(
        not path.replace("\\", "/").startswith("artifacts/milestone-gates/") for path in changes
    )


def _is_ancestor(root: Path, acceptance_sha: str, current_sha: str) -> bool:
    return _git(root, "merge-base", "--is-ancestor", acceptance_sha, current_sha).returncode == 0


def _command_display(command: Command) -> str:
    return command if isinstance(command, str) else shlex.join(command)


def _run_command(command: Command, root: Path) -> int:
    completed = subprocess.run(
        command,
        cwd=root,
        shell=isinstance(command, str),
        capture_output=True,
        check=False,
        text=True,
    )
    return completed.returncode


def _receipt_path(root: Path, milestone: str) -> Path:
    return root / "artifacts" / "milestone-gates" / f"{milestone}.json"


def _read_prior_receipt(root: Path, milestone: str) -> dict[str, object] | None:
    receipt_path = _receipt_path(root, milestone)
    if not receipt_path.is_file():
        return None
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _prior_gate_results(
    root: Path, milestone: str, current_sha: str, config_path: Path
) -> tuple[str, ...]:
    prior_results: list[str] = []
    for prior in MILESTONES[: MILESTONES.index(milestone)]:
        receipt = _read_prior_receipt(root, prior)
        if receipt is None:
            prior_results.append(f"{prior}:missing")
            continue
        if receipt.get("status") != PASS:
            prior_results.append(f"{prior}:not_pass")
            continue
        acceptance_sha = receipt.get("git_sha")
        if not isinstance(acceptance_sha, str) or not _is_ancestor(
            root, acceptance_sha, current_sha
        ):
            prior_results.append(f"{prior}:non_ancestor")
            continue
        try:
            prior_config = _load_config(config_path, prior)
            expected = {
                "dependency_lock_hash": _hash_file(root, "requirements.lock")[1],
                "protected_file_hashes": _hash_paths(root, prior_config["protected_paths"]),
                "evidence_hashes": _hash_paths(root, prior_config["evidence_paths"]),
            }
        except ValueError:
            prior_results.append(f"{prior}:hash_unavailable")
            continue
        if any(receipt.get(key) != value for key, value in expected.items()):
            prior_results.append(f"{prior}:hash_changed")
        else:
            prior_results.append(f"{prior}:PASS")
    return tuple(prior_results)


def _report(
    *,
    status: str,
    commands: Sequence[str],
    exit_codes: Sequence[int],
    git_sha: str,
    dirty: bool,
    dependency_lock_hash: str,
    protected_file_hashes: dict[str, str],
    artifact_hashes: dict[str, str],
    evidence_hashes: dict[str, str],
    prior_gates: Sequence[str],
    fixture_ids: Sequence[str],
    reason: str | None,
) -> GateReport:
    return GateReport(
        status=status,
        commands=tuple(commands),
        exit_codes=tuple(exit_codes),
        git_sha=git_sha,
        dirty=dirty,
        dependency_lock_hash=dependency_lock_hash,
        protected_file_hashes=protected_file_hashes,
        artifact_hashes=artifact_hashes,
        evidence_hashes=evidence_hashes,
        prior_gates=tuple(prior_gates),
        fixture_ids=tuple(fixture_ids),
        reason=reason,
    )


def verify_milestone(
    milestone: str,
    require_prior: bool,
    *,
    repository_root: Path | None = None,
    config_path: Path | None = None,
    command_runner: CommandRunner = _run_command,
) -> GateReport:
    """Run a milestone gate and write a PASS receipt only from a clean start."""
    if milestone not in MILESTONES:
        raise ValueError(f"unknown milestone: {milestone}")
    root = _repository_root(repository_root)
    config_file = (config_path or root / "configs" / "milestones.yaml").resolve()
    config = _load_config(config_file, milestone)
    commands = config["commands"]
    fixture_ids = config["fixture_ids"]
    if not isinstance(commands, list) or not all(
        isinstance(command, (str, list)) for command in commands
    ):
        raise ValueError(f"invalid commands for {milestone}")
    if not isinstance(fixture_ids, list) or not all(
        isinstance(value, str) for value in fixture_ids
    ):
        raise ValueError(f"invalid fixture identifiers for {milestone}")

    git_sha = _git_sha(root)
    dirty = _is_dirty_at_start(root)
    dependency_lock_hash = _hash_file(root, "requirements.lock")[1]
    protected_hashes = _hash_paths(root, config["protected_paths"])
    evidence_hashes = _hash_paths(root, config["evidence_paths"])
    prior_gates = (
        _prior_gate_results(root, milestone, git_sha, config_file) if require_prior else ()
    )
    command_text = tuple(_command_display(command) for command in commands)

    if dirty:
        return _report(
            status=REJECTED,
            commands=command_text,
            exit_codes=(),
            git_sha=git_sha,
            dirty=True,
            dependency_lock_hash=dependency_lock_hash,
            protected_file_hashes=protected_hashes,
            artifact_hashes=evidence_hashes,
            evidence_hashes=evidence_hashes,
            prior_gates=prior_gates,
            fixture_ids=fixture_ids,
            reason="worktree_dirty_at_verification_start",
        )
    if require_prior and any(not result.endswith(":PASS") for result in prior_gates):
        return _report(
            status=REJECTED,
            commands=command_text,
            exit_codes=(),
            git_sha=git_sha,
            dirty=False,
            dependency_lock_hash=dependency_lock_hash,
            protected_file_hashes=protected_hashes,
            artifact_hashes=evidence_hashes,
            evidence_hashes=evidence_hashes,
            prior_gates=prior_gates,
            fixture_ids=fixture_ids,
            reason="required_prior_gate_rejected",
        )

    exit_codes = tuple(command_runner(command, root) for command in commands)
    status = PASS if all(code == 0 for code in exit_codes) else REJECTED
    report = _report(
        status=status,
        commands=command_text,
        exit_codes=exit_codes,
        git_sha=git_sha,
        dirty=False,
        dependency_lock_hash=dependency_lock_hash,
        protected_file_hashes=protected_hashes,
        artifact_hashes=evidence_hashes,
        evidence_hashes=evidence_hashes,
        prior_gates=prior_gates,
        fixture_ids=fixture_ids,
        reason=None if status == PASS else "gate_command_failed",
    )
    if status == PASS:
        receipt_path = _receipt_path(root, milestone)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = receipt_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(asdict(report), sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary_path, receipt_path)
    return report


def main(arguments: Sequence[str] | None = None) -> int:
    """Expose milestone verification as a deterministic JSON CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("milestone", choices=MILESTONES)
    parser.add_argument("--require-prior", action="store_true")
    parsed = parser.parse_args(arguments)
    try:
        report = verify_milestone(parsed.milestone, parsed.require_prior)
    except ValueError as error:
        print(json.dumps({"reason": str(error), "status": REJECTED}, sort_keys=True))
        return 1
    print(json.dumps(asdict(report), sort_keys=True))
    return 0 if report.status == PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
