"""Reject work that is ahead of its milestone or outside QuantLab V1."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

MILESTONES = tuple(f"M{number}" for number in range(10))
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_SCOPE_VIOLATION = 2

PACKAGE_MILESTONES = {
    "quantlab": "M0",
    "apps/cli": "M0",
    "apps/scheduler": "M0",
    "apps/worker": "M0",
    "quantlab/application": "M0",
    "quantlab/common": "M0",
    "quantlab/domain": "M0",
    "quantlab/infrastructure": "M0",
    "quantlab/data": "M1",
    "quantlab/universe": "M1",
    "quantlab/factors": "M2",
    "quantlab/analytics": "M3",
    "quantlab/backtest": "M3",
    "quantlab/portfolio": "M3",
    "quantlab/validation": "M4",
    "quantlab/ml": "M5",
    "quantlab/paper": "M6",
    "apps/mcp": "M7",
    "quantlab/agents": "M7",
    "quantlab/research": "M7",
    "apps/api": "M8",
    "apps/web": "M8",
}

FORBIDDEN_V1_FEATURE_RULES = (
    ("live_money", r"\blive[-_\s]+(?:money|trading)\b"),
    ("intraday", r"\bintraday\b"),
    ("tick_data", r"\btick[-_\s]+data\b"),
    ("high_frequency", r"\b(?:high[-_\s]+frequency|hft)\b"),
    ("options", r"\boptions?\b"),
    ("derivatives", r"\bderivatives?\b"),
    ("futures", r"\bfutures?\b"),
    ("forex", r"\bforex\b"),
    ("crypto", r"\bcrypto(?:currency)?\b"),
    ("shorting", r"\b(?:shorting|short[-_\s]+selling)\b"),
    ("leverage", r"\bleverag(?:e|ed)\b"),
    ("borrow_model", r"\bborrow[-_\s]+models?\b"),
    ("reinforcement_learning", r"\breinforcement[-_\s]+learning\b"),
    ("lstm", r"\blstms?\b"),
    ("transformer", r"\btransformers?\b"),
    ("alternative_data", r"\balternative[-_\s]+data\b"),
    ("paid_data", r"\bpaid[-_\s]+data\b"),
    ("factor_library", r"\bfactor[-_\s]+librar(?:y|ies)\b"),
    ("arbitrary_strategy_code", r"\barbitrary[-_\s]+strategy[-_\s]+code\b"),
    ("agent_swarm", r"\bagent[-_\s]+swarms?\b"),
    ("kubernetes", r"\bkubernetes\b"),
    ("spark", r"\bspark\b"),
    ("multi_tenancy", r"\bmulti[-_\s]+tenan(?:cy|t)\b"),
    ("tax_accounting", r"\btax[-_\s]+accounting\b"),
)
PREMATURE_DEPENDENCIES = (
    ("lightgbm", "M5"),
    ("anthropic", "M7"),
    ("langchain", "M7"),
    ("llama-index", "M7"),
    ("mcp", "M7"),
    ("openai", "M7"),
    ("fastapi", "M8"),
)
PACKAGE_ROOTS = ("apps", "quantlab")
CONTENT_ROOTS = (*PACKAGE_ROOTS, "configs")
CONTENT_SUFFIXES = {".cfg", ".ini", ".json", ".lock", ".py", ".toml", ".txt", ".yaml", ".yml"}
DEPENDENCY_ARTIFACTS = ("pyproject.toml", "requirements.lock")


def emit(payload: dict[str, object]) -> None:
    """Write a deterministic, machine-readable result."""
    print(json.dumps(payload, sort_keys=True))


def package_milestone(package: str) -> str | None:
    """Return the milestone that first permits a package boundary."""
    for package_root in sorted(PACKAGE_MILESTONES, key=len, reverse=True):
        if package == package_root or package.startswith(f"{package_root}/"):
            return PACKAGE_MILESTONES[package_root]
    return None


def package_violations(root: Path, milestone: str) -> list[dict[str, str]]:
    """Find package directories that are too early or unapproved."""
    current_index = MILESTONES.index(milestone)
    violations: list[dict[str, str]] = []
    packages: set[str] = set()
    for source_root in PACKAGE_ROOTS:
        source_path = root / source_root
        if not source_path.exists():
            continue
        if (source_path / "__init__.py").is_file():
            packages.add(source_root)
        packages.update(
            directory.relative_to(root).as_posix()
            for directory in source_path.rglob("*")
            if directory.is_dir() and not directory.name.startswith((".", "__"))
        )

    for package in sorted(packages):
        available_in = package_milestone(package)
        if available_in is None:
            violations.append({"kind": "unapproved_package", "path": package})
        elif MILESTONES.index(available_in) > current_index:
            violations.append(
                {
                    "available_in": available_in,
                    "kind": "premature_package",
                    "path": package,
                }
            )
    return violations


def scoped_files(root: Path) -> list[Path]:
    """Return source and configuration files whose content can define scope."""
    files = {
        path
        for content_root in CONTENT_ROOTS
        if (content_path := root / content_root).exists()
        for path in content_path.rglob("*")
        if path.is_file() and path.suffix.lower() in CONTENT_SUFFIXES
    }
    files.update(
        root / artifact for artifact in DEPENDENCY_ARTIFACTS if (root / artifact).is_file()
    )
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def read_scope_text(path: Path) -> str:
    """Read a scoped file without allowing encoding variance to skip a rule."""
    return path.read_text(encoding="utf-8", errors="replace").lower()


def feature_violations(root: Path) -> list[dict[str, str]]:
    """Find forbidden V1 capabilities in scoped names and contents."""
    files = scoped_files(root)
    violations: list[dict[str, str]] = []
    for rule, pattern in FORBIDDEN_V1_FEATURE_RULES:
        expression = re.compile(pattern)
        for source_path in files:
            relative_path = source_path.relative_to(root).as_posix()
            if expression.search(f"{relative_path.lower()}\n{read_scope_text(source_path)}"):
                violations.append(
                    {
                        "kind": "forbidden_v1_feature",
                        "path": relative_path,
                        "rule": rule,
                    }
                )
    return violations


def dependency_violations(root: Path, milestone: str) -> list[dict[str, str]]:
    """Find dependencies whose assigned milestone has not been reached."""
    current_index = MILESTONES.index(milestone)
    violations: list[dict[str, str]] = []
    for source_path in scoped_files(root):
        relative_path = source_path.relative_to(root).as_posix()
        text = read_scope_text(source_path)
        for dependency, available_in in PREMATURE_DEPENDENCIES:
            expression = re.compile(rf"\b{re.escape(dependency)}\b")
            if expression.search(text) and MILESTONES.index(available_in) > current_index:
                violations.append(
                    {
                        "available_in": available_in,
                        "dependency": dependency,
                        "kind": "premature_dependency",
                        "path": relative_path,
                    }
                )
    return violations


def check_scope(root: Path, milestone: str) -> list[dict[str, str]]:
    """Collect deterministic scope violations for a repository root."""
    return [
        *package_violations(root, milestone),
        *feature_violations(root),
        *dependency_violations(root, milestone),
    ]


def main(arguments: Sequence[str] | None = None) -> int:
    """Check the current repository against the requested milestone."""
    arguments = sys.argv[1:] if arguments is None else arguments
    if len(arguments) != 1 or arguments[0] not in MILESTONES:
        emit(
            {
                "allowed_milestones": list(MILESTONES),
                "status": "invalid_request",
            }
        )
        return EXIT_USAGE

    milestone = arguments[0]
    violations = check_scope(Path.cwd(), milestone)
    if violations:
        emit(
            {
                "milestone": milestone,
                "status": "rejected",
                "violations": violations,
            }
        )
        return EXIT_SCOPE_VIOLATION

    emit({"milestone": milestone, "status": "ok", "violations": []})
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
