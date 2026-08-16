"""Verify deterministic, committed QuantLab milestone acceptance receipts."""

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
SCHEMA_VERSION = 2
type Command = str | Sequence[str]
type CommandRunner = Callable[[Command, Path], int]


@dataclass(frozen=True, slots=True)
class GateReport:
    schema_version: int
    milestone: str
    status: str
    commands: tuple[str, ...]
    exit_codes: tuple[int, ...]
    git_sha: str
    dirty: bool
    dependency_lock_hash: str
    config_hash: str
    protected_file_hashes: dict[str, str]
    artifact_hashes: dict[str, str]
    evidence_hashes: dict[str, str]
    prior_gates: tuple[str, ...]
    fixture_ids: tuple[str, ...]
    reason: str | None = None


def _safe_path(root: Path, value: object, *, must_exist: bool = False) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("configured paths must be non-empty strings")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe repository-relative path: {value!r}")
    current = root
    for part in relative.parts:
        current /= part
        if current.exists() and current.is_symlink():
            raise ValueError(f"symlink path is not allowed: {value!r}")
    candidate = current.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"path escapes repository: {value!r}") from error
    if must_exist and not candidate.exists():
        raise ValueError(f"required path is missing: {value}")
    return candidate


def _hash_path(root: Path, value: object) -> tuple[str, str]:
    path = _safe_path(root, value, must_exist=True)
    relative = path.relative_to(root).as_posix()
    if path.is_file():
        return relative, hashlib.sha256(path.read_bytes()).hexdigest()
    if not path.is_dir():
        raise ValueError(f"unsupported path type: {value}")
    digest = hashlib.sha256()
    for child in sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix()):
        if child.is_symlink():
            raise ValueError(f"symlink path is not allowed: {value!r}")
        if child.is_file():
            name = child.relative_to(path).as_posix().encode("utf-8")
            digest.update(name + b"\0" + hashlib.sha256(child.read_bytes()).digest())
    return relative, digest.hexdigest()


def _hash_paths(root: Path, values: object) -> dict[str, str]:
    if not isinstance(values, list):
        raise ValueError("configured path lists must be lists")
    return dict(sorted(_hash_path(root, value) for value in values))


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments], cwd=root, text=True, capture_output=True, check=False
    )


def _git_sha(root: Path) -> str:
    completed = _git(root, "rev-parse", "HEAD")
    if completed.returncode:
        raise ValueError("milestone verification requires a Git commit")
    return completed.stdout.strip()


def _status_lines(root: Path) -> tuple[str, ...]:
    completed = _git(root, "status", "--porcelain", "--untracked-files=all")
    if completed.returncode:
        raise ValueError("milestone verification requires a Git worktree")
    return tuple(line for line in completed.stdout.splitlines() if line)


def _is_dirty(root: Path) -> bool:
    return bool(_status_lines(root))


def _config_path(root: Path, config_path: Path | None) -> Path:
    default = root / "configs" / "milestones.yaml"
    candidate = (config_path or default).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("milestone configuration must be inside the repository") from error
    if candidate != default.resolve():
        raise ValueError("milestone configuration must use configs/milestones.yaml")
    return _safe_path(root, candidate.relative_to(root).as_posix(), must_exist=True)


def _load_config(
    root: Path, milestone: str, config_path: Path | None
) -> tuple[Path, Mapping[str, object]]:
    path = _config_path(root, config_path)
    tracked = _git(root, "ls-files", "--error-unmatch", path.relative_to(root).as_posix())
    if tracked.returncode:
        raise ValueError("milestone configuration must be tracked")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid milestone configuration") from error
    milestones = payload.get("milestones") if isinstance(payload, dict) else None
    if not isinstance(milestones, dict) or milestone not in milestones:
        raise ValueError(f"milestone is not configured: {milestone}")
    config = milestones[milestone]
    required = ("commands", "evidence_paths", "fixture_ids", "protected_paths")
    if not isinstance(config, dict) or any(key not in config for key in required):
        raise ValueError(f"incomplete configuration for {milestone}")
    return path, config


def _command_display(command: Command) -> str:
    return command if isinstance(command, str) else shlex.join(command)


def _run_command(command: Command, root: Path) -> int:
    return subprocess.run(command, cwd=root, shell=isinstance(command, str), check=False).returncode


def _receipt_path(root: Path, milestone: str) -> Path:
    return _safe_path(root, f"artifacts/milestone-gates/{milestone}.json")


def _expected_commit_message(milestone: str) -> str:
    return f"chore(gate): accept {milestone}"


def _receipt_blob(root: Path, revision: str, relative: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative}"], cwd=root, capture_output=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def _prior_result(root: Path, milestone: str, current_sha: str, config_path: Path) -> str:
    path = _receipt_path(root, milestone)
    relative = path.relative_to(root).as_posix()
    if not path.is_file():
        return f"{milestone}:missing"
    if _git(root, "ls-files", "--error-unmatch", relative).returncode:
        return f"{milestone}:untracked_or_modified"
    if _git(root, "diff", "--quiet", "HEAD", "--", relative).returncode:
        return f"{milestone}:untracked_or_modified"
    head_blob = _receipt_blob(root, "HEAD", relative)
    if head_blob is None:
        return f"{milestone}:untracked_or_modified"
    additions = _git(root, "log", "--format=%H", "--diff-filter=A", "--", relative)
    acceptance = additions.stdout.splitlines()
    if len(acceptance) != 1:
        return f"{milestone}:untracked_or_modified"
    acceptance_sha = acceptance[0]
    if _git(
        root, "log", "-1", "--format=%s", acceptance_sha
    ).stdout.strip() != _expected_commit_message(milestone):
        return f"{milestone}:invalid_acceptance_commit"
    if _git(root, "merge-base", "--is-ancestor", acceptance_sha, current_sha).returncode:
        return f"{milestone}:non_ancestor"
    if _receipt_blob(root, acceptance_sha, relative) != head_blob:
        return f"{milestone}:untracked_or_modified"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return f"{milestone}:malformed"
    try:
        _, config = _load_config(root, milestone, config_path)
        commands = config["commands"]
        fixture_ids = config["fixture_ids"]
        if not isinstance(commands, list) or not isinstance(fixture_ids, list):
            return f"{milestone}:malformed"
        parent = _git(root, "rev-parse", f"{acceptance_sha}^").stdout.strip()
        expected = {
            "schema_version": SCHEMA_VERSION,
            "milestone": milestone,
            "status": PASS,
            "commands": [_command_display(command) for command in commands],
            "exit_codes": [0] * len(commands),
            "git_sha": parent,
            "dirty": False,
            "dependency_lock_hash": _hash_path(root, "requirements.lock")[1],
            "config_hash": _hash_path(root, config_path.relative_to(root).as_posix())[1],
            "protected_file_hashes": _hash_paths(root, config["protected_paths"]),
            "artifact_hashes": _hash_paths(root, config["evidence_paths"]),
            "evidence_hashes": _hash_paths(root, config["evidence_paths"]),
            "prior_gates": [f"{item}:PASS" for item in MILESTONES[: MILESTONES.index(milestone)]],
            "fixture_ids": fixture_ids,
            "reason": None,
        }
    except ValueError:
        return f"{milestone}:hash_changed"
    hashed_fields = (
        "dependency_lock_hash",
        "config_hash",
        "protected_file_hashes",
        "artifact_hashes",
        "evidence_hashes",
    )
    if any(receipt.get(key) != expected[key] for key in hashed_fields):
        return f"{milestone}:hash_changed"
    if set(receipt) != set(expected) or any(
        receipt.get(key) != value for key, value in expected.items()
    ):
        return f"{milestone}:invalid_receipt"
    return f"{milestone}:PASS"


def _report(
    milestone: str,
    status: str,
    commands: Sequence[str],
    codes: Sequence[int],
    sha: str,
    dirty: bool,
    lock_hash: str,
    config_hash: str,
    protected: dict[str, str],
    evidence: dict[str, str],
    priors: Sequence[str],
    fixtures: Sequence[str],
    reason: str | None,
) -> GateReport:
    return GateReport(
        SCHEMA_VERSION,
        milestone,
        status,
        tuple(commands),
        tuple(codes),
        sha,
        dirty,
        lock_hash,
        config_hash,
        protected,
        evidence,
        evidence,
        tuple(priors),
        tuple(fixtures),
        reason,
    )


def verify_milestone(
    milestone: str,
    require_prior: bool,
    *,
    repository_root: Path | None = None,
    config_path: Path | None = None,
    command_runner: CommandRunner = _run_command,
) -> GateReport:
    """Run one gate; only M0 may run without mandatory prior enforcement."""
    if milestone not in MILESTONES:
        raise ValueError(f"unknown milestone: {milestone}")
    root = (repository_root or Path.cwd()).resolve()
    config_file, config = _load_config(root, milestone, config_path)
    _receipt_path(root, milestone)
    commands, fixtures, evidence_paths = (
        config["commands"],
        config["fixture_ids"],
        config["evidence_paths"],
    )
    if not isinstance(commands, list) or not all(
        isinstance(item, (str, list)) for item in commands
    ):
        raise ValueError("invalid commands")
    if not isinstance(fixtures, list) or not all(isinstance(item, str) for item in fixtures):
        raise ValueError("invalid fixture identifiers")
    if not isinstance(evidence_paths, list) or not all(
        isinstance(item, str) for item in evidence_paths
    ):
        raise ValueError("invalid evidence paths")
    sha, dirty = _git_sha(root), _is_dirty(root)
    lock_hash = _hash_path(root, "requirements.lock")[1]
    config_hash = _hash_path(root, config_file.relative_to(root).as_posix())[1]
    protected = _hash_paths(root, config["protected_paths"])
    texts = tuple(_command_display(item) for item in commands)
    priors = tuple(
        _prior_result(root, prior, sha, config_file)
        for prior in MILESTONES[: MILESTONES.index(milestone)]
    )
    if (
        dirty
        or (milestone != "M0" and not require_prior)
        or any(not item.endswith(":PASS") for item in priors)
    ):
        return _report(
            milestone,
            REJECTED,
            texts,
            (),
            sha,
            dirty,
            lock_hash,
            config_hash,
            protected,
            {},
            priors,
            fixtures,
            "dirty_or_prior_rejected",
        )
    codes = tuple(command_runner(item, root) for item in commands)
    post_sha, post_dirty = _git_sha(root), _is_dirty(root)
    evidence = _hash_paths(root, evidence_paths)
    allowed = set(evidence_paths)
    changed = _status_lines(root)
    allowed_untracked = all(
        line.startswith("?? ")
        and any(
            (changed_path := line[3:].replace("\\", "/")) == allowed_path
            or changed_path.startswith(f"{allowed_path}/")
            for allowed_path in allowed
        )
        for line in changed
    )
    if (
        any(code for code in codes)
        or post_sha != sha
        or post_dirty
        and not allowed_untracked
        or _hash_paths(root, config["protected_paths"]) != protected
    ):
        return _report(
            milestone,
            REJECTED,
            texts,
            codes,
            post_sha,
            post_dirty,
            lock_hash,
            config_hash,
            protected,
            evidence,
            priors,
            fixtures,
            "command_mutated_repository_or_failed",
        )
    report = _report(
        milestone,
        PASS,
        texts,
        codes,
        post_sha,
        False,
        lock_hash,
        config_hash,
        protected,
        evidence,
        priors,
        fixtures,
        None,
    )
    path = _receipt_path(root, milestone)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _safe_path(root, f"artifacts/milestone-gates/{milestone}.tmp")
    temporary.write_text(json.dumps(asdict(report), sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return report


def main(arguments: Sequence[str] | None = None) -> int:
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
