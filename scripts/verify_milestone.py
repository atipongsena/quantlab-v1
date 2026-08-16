"""Verify deterministic, committed QuantLab milestone acceptance receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

MILESTONES = tuple(f"M{number}" for number in range(10))
PASS = "PASS"
REJECTED = "REJECTED"
SCHEMA_VERSION = 3
TRANSCRIPT_SCHEMA_VERSION = 1
CHALLENGE_SCHEMA_VERSION = 1
GOLDEN_APPROVAL_SCHEMA_VERSION = 1
_CANONICAL_CONFIG_SHA256 = "dc8358eeaeae867eeaabc34176d39e620977668f8d2b4ba880d8d5155fb8e75a"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
type Command = str | Sequence[str]


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
    transcript_hash: str
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
        if current.is_symlink():
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


def _validate_config_paths(root: Path, config: Mapping[str, object]) -> None:
    for key in ("protected_paths", "evidence_paths"):
        values = config.get(key)
        if not isinstance(values, list):
            raise ValueError("configured path lists must be lists")
        for value in values:
            _safe_path(root, value)
    approval = config.get("golden_approval")
    if approval is not None:
        if not isinstance(approval, dict):
            raise ValueError("invalid golden approval policy")
        for key in ("path", "directory"):
            _safe_path(root, approval.get(key))


def _golden_approval_failure(
    root: Path, milestone: str, current_sha: str, config: Mapping[str, object]
) -> str | None:
    approval = config.get("golden_approval")
    if milestone != "M3":
        if approval is not None:
            raise ValueError("golden approval policy is only valid for M3")
        return None
    if not isinstance(approval, dict) or set(approval) != {
        "path",
        "directory",
        "commit_subject",
    }:
        raise ValueError("invalid golden approval policy")
    path_value = approval["path"]
    directory_value = approval["directory"]
    subject_value = approval["commit_subject"]
    if not isinstance(subject_value, str) or not subject_value:
        raise ValueError("invalid golden approval policy")
    path = _safe_path(root, path_value)
    directory = _safe_path(root, directory_value, must_exist=True)
    relative = path.relative_to(root).as_posix()
    if not path.is_file():
        return "golden_approval_missing"
    if (
        _git(root, "ls-files", "--error-unmatch", relative).returncode
        or _git(root, "diff", "--quiet", "HEAD", "--", relative).returncode
    ):
        return "golden_approval_provenance_mismatch"
    additions = _git(
        root, "log", "--format=%H", "--diff-filter=A", "--", relative
    ).stdout.splitlines()
    if len(additions) != 1:
        return "golden_approval_provenance_mismatch"
    commit = additions[0]
    changed_paths = tuple(
        _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", commit)
        .stdout.strip()
        .splitlines()
    )
    if (
        _git(root, "merge-base", "--is-ancestor", commit, current_sha).returncode
        or _git(root, "log", "-1", "--format=%s", commit).stdout.strip() != subject_value
        or changed_paths != (relative,)
        or _receipt_blob(root, commit, relative) != _receipt_blob(root, "HEAD", relative)
    ):
        return "golden_approval_provenance_mismatch"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "golden_approval_provenance_mismatch"
    expected_digest = _hash_path(root, directory.relative_to(root).as_posix())[1]
    expected = {
        "schema_version": GOLDEN_APPROVAL_SCHEMA_VERSION,
        "milestone": "M3",
        "directory": directory.relative_to(root).as_posix(),
        "directory_sha256": expected_digest,
    }
    if not isinstance(payload, dict) or payload.get("directory_sha256") != expected_digest:
        return "golden_approval_digest_mismatch"
    if payload != expected:
        return "golden_approval_provenance_mismatch"
    return None


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


def _status_lines_except(root: Path, paths: Sequence[Path]) -> tuple[str, ...]:
    excluded = {path.relative_to(root).as_posix() for path in paths}
    remaining: list[str] = []
    for line in _status_lines(root):
        changed = line[3:].replace("\\", "/")
        if changed not in excluded:
            remaining.append(line)
    return tuple(remaining)


def _config_path(root: Path) -> Path:
    return _safe_path(root, "configs/milestones.yaml", must_exist=True)


def _load_config(root: Path, milestone: str) -> tuple[Path, Mapping[str, object]]:
    path = _config_path(root)
    tracked = _git(root, "ls-files", "--error-unmatch", path.relative_to(root).as_posix())
    if tracked.returncode:
        raise ValueError("milestone configuration must be tracked")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid milestone configuration") from error
    if not isinstance(payload, dict):
        raise ValueError("invalid milestone configuration")
    if hashlib.sha256(path.read_bytes()).hexdigest() != _CANONICAL_CONFIG_SHA256:
        raise ValueError("milestone configuration differs from canonical policy")
    milestones = payload.get("milestones")
    if not isinstance(milestones, dict) or milestone not in milestones:
        raise ValueError(f"milestone is not configured: {milestone}")
    if tuple(milestones) != MILESTONES:
        raise ValueError("milestone configuration must list M0 through M9 in canonical order")
    config = milestones[milestone]
    required = ("commands", "evidence_paths", "fixture_ids", "protected_paths")
    if (
        not isinstance(config, dict)
        or any(key not in config for key in required)
        or any(not isinstance(config[key], list) or not config[key] for key in required)
    ):
        raise ValueError(f"incomplete configuration for {milestone}")
    return path, config


def _command_display(command: Command) -> str:
    return command if isinstance(command, str) else shlex.join(command)


def _optional_hash_paths(root: Path, values: object) -> dict[str, str]:
    if not isinstance(values, list):
        raise ValueError("configured path lists must be lists")
    hashes: dict[str, str] = {}
    for value in values:
        path = _safe_path(root, value)
        relative = path.relative_to(root).as_posix()
        hashes[relative] = _hash_path(root, value)[1] if path.exists() else "MISSING"
    return dict(sorted(hashes.items()))


def _state_sha256(root: Path, config_file: Path, config: Mapping[str, object]) -> str:
    payload = {
        "git_sha": _git_sha(root),
        "status": list(_status_lines(root)),
        "config_hash": _hash_path(root, config_file.relative_to(root).as_posix())[1],
        "protected_file_hashes": _hash_paths(root, config["protected_paths"]),
        "evidence_hashes": _optional_hash_paths(root, config["evidence_paths"]),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _run_command_with_evidence(
    command: Command, root: Path, config_file: Path, config: Mapping[str, object]
) -> tuple[int, dict[str, object]]:
    before = _state_sha256(root, config_file, config)
    completed = subprocess.run(
        command,
        cwd=root,
        shell=isinstance(command, str),
        check=False,
        capture_output=True,
    )
    after = _state_sha256(root, config_file, config)
    evidence: dict[str, object] = {
        "command": _command_display(command),
        "exit_code": completed.returncode,
        "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
        "state_before_sha256": before,
        "state_after_sha256": after,
    }
    return completed.returncode, evidence


def _receipt_path(root: Path, milestone: str) -> Path:
    return _safe_path(root, f"artifacts/milestone-gates/{milestone}.json")


def _transcript_path(root: Path, milestone: str) -> Path:
    return _safe_path(root, f"artifacts/milestone-gates/{milestone}.transcript.json")


def _challenge_path(root: Path, milestone: str) -> Path:
    return _safe_path(root, f"artifacts/milestone-gates/{milestone}.challenge.json")


def _expected_commit_message(milestone: str) -> str:
    return f"chore(gate): accept {milestone}"


def _expected_challenge_message(milestone: str) -> str:
    return f"chore(gate): challenge {milestone}"


def _receipt_blob(root: Path, revision: str, relative: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative}"], cwd=root, capture_output=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def _snapshot_sha256(
    git_sha: str, config_hash: str, protected_file_hashes: Mapping[str, str]
) -> str:
    encoded = json.dumps(
        {
            "git_sha": git_sha,
            "config_hash": config_hash,
            "protected_file_hashes": protected_file_hashes,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _challenge_payload(
    milestone: str,
    git_sha: str,
    config_hash: str,
    protected_file_hashes: dict[str, str],
) -> dict[str, object]:
    return {
        "schema_version": CHALLENGE_SCHEMA_VERSION,
        "milestone": milestone,
        "nonce": secrets.token_hex(32),
        "prepared_git_sha": git_sha,
        "config_hash": config_hash,
        "protected_file_hashes": protected_file_hashes,
        "prepared_state_sha256": _snapshot_sha256(git_sha, config_hash, protected_file_hashes),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def _write_challenge(
    root: Path,
    milestone: str,
    git_sha: str,
    config_hash: str,
    protected_file_hashes: dict[str, str],
) -> None:
    path = _challenge_path(root, milestone)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _safe_path(root, f"artifacts/milestone-gates/{milestone}.challenge.tmp")
    payload = _challenge_payload(milestone, git_sha, config_hash, protected_file_hashes)
    temporary.write_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))
    os.replace(temporary, path)


def _challenge_details(
    root: Path,
    milestone: str,
    current_sha: str,
    config_hash: str,
    protected_file_hashes: dict[str, str],
    *,
    require_current: bool = False,
) -> tuple[bytes, str] | None:
    path = _challenge_path(root, milestone)
    relative = path.relative_to(root).as_posix()
    if not path.is_file():
        return None
    if _git(root, "ls-files", "--error-unmatch", relative).returncode:
        return None
    if _git(root, "diff", "--quiet", "HEAD", "--", relative).returncode:
        raise ValueError("challenge must be committed and unchanged")
    commit = _git(root, "log", "-1", "--format=%H", "--", relative).stdout.strip()
    if not commit or _git(root, "merge-base", "--is-ancestor", commit, current_sha).returncode:
        raise ValueError("challenge commit is not an ancestor")
    if require_current and commit != current_sha:
        return None
    blob = _receipt_blob(root, "HEAD", relative)
    commit_blob = _receipt_blob(root, commit, relative)
    if blob is None or blob != commit_blob:
        raise ValueError("challenge provenance mismatch")
    try:
        payload = json.loads(blob)
    except json.JSONDecodeError as error:
        raise ValueError("malformed challenge") from error
    parent = _git(root, "rev-parse", f"{commit}^").stdout.strip()
    nonce = payload.get("nonce") if isinstance(payload, dict) else None
    expected = {
        "schema_version": CHALLENGE_SCHEMA_VERSION,
        "milestone": milestone,
        "nonce": nonce,
        "prepared_git_sha": parent,
        "config_hash": config_hash,
        "protected_file_hashes": protected_file_hashes,
        "prepared_state_sha256": _snapshot_sha256(parent, config_hash, protected_file_hashes),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    changed_paths = tuple(
        _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", commit)
        .stdout.strip()
        .splitlines()
    )
    subject = _git(root, "log", "-1", "--format=%s", commit).stdout.strip()
    if (
        not isinstance(nonce, str)
        or _SHA256_PATTERN.fullmatch(nonce) is None
        or payload != expected
        or subject != _expected_challenge_message(milestone)
        or changed_paths != (relative,)
    ):
        raise ValueError("challenge provenance mismatch")
    return blob, commit


def _latest_acceptance_commit(
    root: Path, milestone: str, current_sha: str, receipt_relative: str, transcript_relative: str
) -> str | None:
    history = _git(root, "log", "--format=%H", "--", receipt_relative, transcript_relative)
    for candidate in history.stdout.splitlines():
        subject = _git(root, "log", "-1", "--format=%s", candidate).stdout.strip()
        if subject != _expected_commit_message(milestone):
            continue
        if _git(root, "merge-base", "--is-ancestor", candidate, current_sha).returncode:
            continue
        candidate_receipt = _receipt_blob(root, candidate, receipt_relative)
        candidate_transcript = _receipt_blob(root, candidate, transcript_relative)
        if candidate_receipt == _receipt_blob(
            root, "HEAD", receipt_relative
        ) and candidate_transcript == _receipt_blob(root, "HEAD", transcript_relative):
            return candidate
    return None


def _prior_transcript_hashes(root: Path, milestone: str) -> list[str]:
    hashes: list[str] = []
    for prior in MILESTONES[: MILESTONES.index(milestone)]:
        try:
            payload = json.loads(_receipt_path(root, prior).read_text(encoding="utf-8"))
            value = payload["transcript_hash"]
        except (KeyError, TypeError, json.JSONDecodeError, OSError):
            return []
        if not isinstance(value, str):
            return []
        hashes.append(value)
    return hashes


def _valid_command_runs(payload: object, commands: Sequence[str]) -> bool:
    if not isinstance(payload, list) or len(payload) != len(commands):
        return False
    expected_keys = {
        "command",
        "exit_code",
        "stdout_sha256",
        "stderr_sha256",
        "state_before_sha256",
        "state_after_sha256",
    }
    previous_after: str | None = None
    for expected_command, item in zip(commands, payload, strict=True):
        if not isinstance(item, dict) or set(item) != expected_keys:
            return False
        if item["command"] != expected_command or item["exit_code"] != 0:
            return False
        hashes = (
            item["stdout_sha256"],
            item["stderr_sha256"],
            item["state_before_sha256"],
            item["state_after_sha256"],
        )
        if any(
            not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None
            for value in hashes
        ):
            return False
        if previous_after is not None and item["state_before_sha256"] != previous_after:
            return False
        previous_after = item["state_after_sha256"]
    return True


def _prior_result(
    root: Path,
    milestone: str,
    current_sha: str,
    config_path: Path,
) -> str:
    path = _receipt_path(root, milestone)
    relative = path.relative_to(root).as_posix()
    transcript = _transcript_path(root, milestone)
    transcript_relative = transcript.relative_to(root).as_posix()
    challenge = _challenge_path(root, milestone)
    challenge_relative = challenge.relative_to(root).as_posix()
    if not path.is_file():
        return f"{milestone}:missing"
    if not transcript.is_file():
        return f"{milestone}:missing_transcript"
    if not challenge.is_file():
        return f"{milestone}:missing_challenge"
    if _git(
        root, "ls-files", "--error-unmatch", relative, transcript_relative, challenge_relative
    ).returncode:
        return f"{milestone}:untracked_or_modified"
    if _git(
        root, "diff", "--quiet", "HEAD", "--", relative, transcript_relative, challenge_relative
    ).returncode:
        return f"{milestone}:untracked_or_modified"
    head_blob = _receipt_blob(root, "HEAD", relative)
    transcript_blob = _receipt_blob(root, "HEAD", transcript_relative)
    if head_blob is None or transcript_blob is None:
        return f"{milestone}:untracked_or_modified"
    acceptance_sha = _latest_acceptance_commit(
        root, milestone, current_sha, relative, transcript_relative
    )
    if acceptance_sha is None:
        return f"{milestone}:invalid_acceptance_commit"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        transcript_payload = json.loads(transcript.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return f"{milestone}:malformed"
    try:
        _, config = _load_config(root, milestone)
        commands = config["commands"]
        fixture_ids = config["fixture_ids"]
        if not isinstance(commands, list) or not isinstance(fixture_ids, list):
            return f"{milestone}:malformed"
        parent = _git(root, "rev-parse", f"{acceptance_sha}^").stdout.strip()
        expected_commands = [_command_display(command) for command in commands]
        expected_config_hash = _hash_path(root, config_path.relative_to(root).as_posix())[1]
        expected_protected = _hash_paths(root, config["protected_paths"])
        expected = {
            "schema_version": SCHEMA_VERSION,
            "milestone": milestone,
            "status": PASS,
            "commands": expected_commands,
            "exit_codes": [0] * len(commands),
            "git_sha": parent,
            "dirty": False,
            "dependency_lock_hash": _hash_path(root, "requirements.lock")[1],
            "config_hash": expected_config_hash,
            "transcript_hash": hashlib.sha256(transcript_blob).hexdigest(),
            "protected_file_hashes": expected_protected,
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
        "transcript_hash",
    )
    if any(receipt.get(key) != expected[key] for key in hashed_fields):
        return f"{milestone}:hash_changed"
    try:
        challenge_details = _challenge_details(
            root,
            milestone,
            current_sha,
            expected_config_hash,
            expected_protected,
        )
    except ValueError:
        return f"{milestone}:invalid_challenge"
    if challenge_details is None:
        return f"{milestone}:invalid_challenge"
    challenge_blob, challenge_commit = challenge_details
    if set(receipt) != set(expected) or any(
        receipt.get(key) != value for key, value in expected.items()
    ):
        return f"{milestone}:invalid_receipt"
    transcript_expected = {
        "schema_version": TRANSCRIPT_SCHEMA_VERSION,
        "milestone": milestone,
        "git_sha": parent,
        "commands": expected["commands"],
        "exit_codes": expected["exit_codes"],
        "protected_file_hashes": expected["protected_file_hashes"],
        "evidence_hashes": expected["evidence_hashes"],
        "prior_transcript_hashes": _prior_transcript_hashes(root, milestone),
        "challenge_hash": hashlib.sha256(challenge_blob).hexdigest(),
        "challenge_commit": challenge_commit,
    }
    if not isinstance(transcript_payload, dict) or any(
        transcript_payload.get(key) != value for key, value in transcript_expected.items()
    ):
        return f"{milestone}:invalid_transcript"
    command_runs = transcript_payload.get("command_runs")
    expected_transcript_keys = set(transcript_expected) | {
        "command_runs",
        "execution_start_state_sha256",
        "execution_end_state_sha256",
    }
    if (
        set(transcript_payload) != expected_transcript_keys
        or not _valid_command_runs(command_runs, expected_commands)
        or not isinstance(command_runs, list)
        or transcript_payload["execution_start_state_sha256"]
        != command_runs[0]["state_before_sha256"]
        or transcript_payload["execution_end_state_sha256"]
        != command_runs[-1]["state_after_sha256"]
    ):
        return f"{milestone}:invalid_transcript"
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
    transcript_hash: str,
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
        transcript_hash,
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
) -> GateReport:
    """Run one gate; only M0 may run without mandatory prior enforcement."""
    if milestone not in MILESTONES:
        raise ValueError(f"unknown milestone: {milestone}")
    root = (repository_root or Path.cwd()).resolve()
    config_file, config = _load_config(root, milestone)
    receipt = _receipt_path(root, milestone)
    transcript = _transcript_path(root, milestone)
    _validate_config_paths(root, config)
    commands, fixtures, evidence_paths = (
        config["commands"],
        config["fixture_ids"],
        config["evidence_paths"],
    )
    if not isinstance(commands, list) or not all(
        isinstance(item, str)
        or isinstance(item, list)
        and item
        and all(isinstance(argument, str) for argument in item)
        for item in commands
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
            "",
            protected,
            {},
            priors,
            fixtures,
            "dirty_or_prior_rejected",
        )
    approval_failure = _golden_approval_failure(root, milestone, sha, config)
    if approval_failure is not None:
        return _report(
            milestone,
            REJECTED,
            texts,
            (),
            sha,
            False,
            lock_hash,
            config_hash,
            "",
            protected,
            {},
            priors,
            fixtures,
            approval_failure,
        )
    challenge_details = _challenge_details(
        root,
        milestone,
        sha,
        config_hash,
        protected,
        require_current=True,
    )
    if challenge_details is None:
        _write_challenge(root, milestone, sha, config_hash, protected)
        return _report(
            milestone,
            REJECTED,
            texts,
            (),
            sha,
            False,
            lock_hash,
            config_hash,
            "",
            protected,
            {},
            priors,
            fixtures,
            "challenge_created",
        )
    challenge_blob, challenge_commit = challenge_details
    command_runs: list[dict[str, object]] = []
    code_list: list[int] = []
    for command in commands:
        code, command_evidence = _run_command_with_evidence(command, root, config_file, config)
        code_list.append(code)
        command_runs.append(command_evidence)
    codes = tuple(code_list)
    post_sha = _git_sha(root)
    post_status = _status_lines(root)
    post_dirty = bool(post_status)
    evidence = _hash_paths(root, evidence_paths)
    allowed = set(evidence_paths)
    allowed_untracked = all(
        line.startswith("?? ")
        and any(
            (changed_path := line[3:].replace("\\", "/")) == allowed_path
            or changed_path.startswith(f"{allowed_path}/")
            for allowed_path in allowed
        )
        for line in post_status
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
            "",
            protected,
            evidence,
            priors,
            fixtures,
            "command_mutated_repository_or_failed",
        )
    transcript_payload = {
        "schema_version": TRANSCRIPT_SCHEMA_VERSION,
        "milestone": milestone,
        "git_sha": sha,
        "commands": list(texts),
        "exit_codes": list(codes),
        "protected_file_hashes": protected,
        "evidence_hashes": evidence,
        "prior_transcript_hashes": _prior_transcript_hashes(root, milestone),
        "challenge_hash": hashlib.sha256(challenge_blob).hexdigest(),
        "challenge_commit": challenge_commit,
        "command_runs": command_runs,
        "execution_start_state_sha256": command_runs[0]["state_before_sha256"],
        "execution_end_state_sha256": command_runs[-1]["state_after_sha256"],
    }
    transcript_bytes = json.dumps(transcript_payload, sort_keys=True).encode("utf-8")
    transcript_hash = hashlib.sha256(transcript_bytes).hexdigest()
    report = _report(
        milestone,
        PASS,
        texts,
        codes,
        post_sha,
        False,
        lock_hash,
        config_hash,
        transcript_hash,
        protected,
        evidence,
        priors,
        fixtures,
        None,
    )
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt_temporary = _safe_path(root, f"artifacts/milestone-gates/{milestone}.tmp")
    transcript_temporary = _safe_path(root, f"artifacts/milestone-gates/{milestone}.transcript.tmp")
    receipt_bytes = (json.dumps(asdict(report), sort_keys=True) + "\n").encode("utf-8")
    receipt_temporary.write_text(receipt_bytes.decode("utf-8"), encoding="utf-8", newline="")
    transcript_temporary.write_bytes(transcript_bytes)
    final_sha = _git_sha(root)
    final_status = _status_lines_except(root, (receipt_temporary, transcript_temporary))
    final_evidence = _hash_paths(root, evidence_paths)
    final_protected = _hash_paths(root, config["protected_paths"])
    unchanged = (
        final_sha == post_sha
        and final_evidence == evidence
        and final_protected == protected
        and final_status == post_status
    )
    if not unchanged:
        receipt_temporary.unlink(missing_ok=True)
        transcript_temporary.unlink(missing_ok=True)
        return _report(
            milestone,
            REJECTED,
            texts,
            codes,
            final_sha,
            bool(final_status),
            lock_hash,
            config_hash,
            "",
            final_protected,
            final_evidence,
            priors,
            fixtures,
            "snapshot_changed_before_publish",
        )
    os.replace(transcript_temporary, transcript)
    os.replace(receipt_temporary, receipt)
    published_status = _status_lines_except(root, (receipt, transcript))
    try:
        published_protected = _hash_paths(root, config["protected_paths"])
        published_evidence = _hash_paths(root, evidence_paths)
        published_hashes_match = (
            receipt.is_file()
            and transcript.is_file()
            and receipt.read_bytes() == receipt_bytes
            and transcript.read_bytes() == transcript_bytes
        )
    except (OSError, ValueError):
        published_protected = {}
        published_evidence = {}
        published_hashes_match = False
    published_state_matches = (
        _git_sha(root) == post_sha
        and published_status == post_status
        and published_protected == protected
        and published_evidence == evidence
    )
    if not published_hashes_match or not published_state_matches:
        tombstone = _report(
            milestone,
            REJECTED,
            texts,
            codes,
            _git_sha(root),
            bool(published_status),
            lock_hash,
            config_hash,
            "",
            published_protected,
            published_evidence,
            priors,
            fixtures,
            "publication_changed",
        )
        tombstone_temporary = _safe_path(
            root, f"artifacts/milestone-gates/{milestone}.tombstone.tmp"
        )
        tombstone_temporary.write_text(
            json.dumps(asdict(tombstone), sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(tombstone_temporary, receipt)
        return tombstone
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
