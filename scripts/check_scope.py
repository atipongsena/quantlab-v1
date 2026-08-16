"""Reject work that is ahead of its milestone or outside QuantLab V1."""

from __future__ import annotations

import json
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

FORBIDDEN_V1_FEATURES = (
    "live_money",
    "intraday",
    "tick_data",
    "high_frequency",
    "options",
    "futures",
    "forex",
    "crypto",
    "shorting",
    "leverage",
    "borrow_model",
    "reinforcement_learning",
    "lstm",
    "transformer",
    "alternative_data",
    "paid_data",
    "factor_library",
    "arbitrary_strategy_code",
    "agent_swarm",
    "kubernetes",
    "spark",
    "multi_tenancy",
    "tax_accounting",
)
SOURCE_ROOTS = ("apps", "quantlab")


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
    """Find package initializers that are too early or unapproved."""
    current_index = MILESTONES.index(milestone)
    violations: list[dict[str, str]] = []
    for source_root in SOURCE_ROOTS:
        source_path = root / source_root
        if not source_path.exists():
            continue
        for initializer in sorted(source_path.rglob("__init__.py")):
            package = initializer.parent.relative_to(root).as_posix()
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


def feature_violations(root: Path) -> list[dict[str, str]]:
    """Find source paths that implement an explicit V1 non-goal."""
    source_paths = [
        path
        for source_root in SOURCE_ROOTS
        if (source_path := root / source_root).exists()
        for path in sorted(source_path.rglob("*"))
        if path.is_file()
    ]
    violations: list[dict[str, str]] = []
    for rule in FORBIDDEN_V1_FEATURES:
        for source_path in source_paths:
            relative_path = source_path.relative_to(root).as_posix()
            if rule in relative_path.lower():
                violations.append(
                    {
                        "kind": "forbidden_v1_feature",
                        "path": relative_path,
                        "rule": rule,
                    }
                )
    return violations


def check_scope(root: Path, milestone: str) -> list[dict[str, str]]:
    """Collect deterministic scope violations for a repository root."""
    return [*package_violations(root, milestone), *feature_violations(root)]


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
