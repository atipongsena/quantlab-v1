from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from quantlab.application.doctor import DoctorService


def run_doctor(args: argparse.Namespace) -> int:
    service = DoctorService()
    offline = not getattr(args, "online", False)
    report = service.run(offline=offline)

    print("=" * 60)
    print(f"QuantLab Doctor Report (Environment: {report.environment})")
    print(f"Overall Status: {report.overall_status}")
    print("=" * 60)

    for check in report.checks:
        if check.status == "PASS":
            icon = "[PASS]"
        elif check.status == "WARN":
            icon = "[WARN]"
        else:
            icon = "[FAIL]"
        print(f"{icon:7} {check.name:22} : {check.details}")

    print("-" * 60)
    return 0 if report.overall_status in ("PASS", "WARN") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quantlab",
        description="QuantLab Quantitative Platform",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run system and environment diagnostic checks",
    )
    doctor_parser.add_argument(
        "--offline",
        action="store_true",
        default=True,
        help="Run in offline-only mode without querying external APIs",
    )
    doctor_parser.add_argument(
        "--online",
        action="store_true",
        default=False,
        help="Run with external network checks enabled",
    )
    doctor_parser.set_defaults(func=run_doctor)

    return parser


def app(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if arguments is None else list(arguments))
    if hasattr(args, "func"):
        return int(args.func(args))
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(app())
