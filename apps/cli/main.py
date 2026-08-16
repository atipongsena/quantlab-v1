from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from quantlab.application.dataset_service import DatasetService
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


def run_dataset_build(args: argparse.Namespace) -> int:
    service = DatasetService()
    offline = getattr(args, "offline", True)
    manifest = service.build_dataset(args.config, offline=offline)
    print(f"Dataset '{manifest.dataset_id}' version '{manifest.version}' built successfully.")
    print(f"Manifest Hash: {manifest.manifest_hash}")
    for tbl, cnt in manifest.row_counts.items():
        print(f"  - Table {tbl}: {cnt} rows")
    return 0


def run_dataset_inspect(args: argparse.Namespace) -> int:
    service = DatasetService()
    verify_hash = getattr(args, "verify_hash", False)
    res = service.inspect_dataset(args.dataset_id, verify_hash=verify_hash)
    print(f"Dataset: {res['dataset_id']} (version: {res['version']})")
    print(f"Status: {res['status']}")
    print(f"Manifest Hash: {res['manifest_hash']}")
    if verify_hash:
        print(f"Computed Hash: {res['computed_hash']}")
        print(f"Hash Verified: {res['hash_verified']}")
    return 0 if res["status"] == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quantlab",
        description="QuantLab Quantitative Platform",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # doctor
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

    # dataset
    dataset_parser = subparsers.add_parser(
        "dataset",
        help="Dataset management subcommands",
    )
    dataset_subparsers = dataset_parser.add_subparsers(
        dest="dataset_command", help="Dataset actions"
    )

    build_cmd = dataset_subparsers.add_parser(
        "build",
        help="Build point-in-time dataset from configuration",
    )
    build_cmd.add_argument(
        "config",
        help="Path to dataset configuration YAML file",
    )
    build_cmd.add_argument(
        "--offline",
        action="store_true",
        default=True,
        help="Run in offline mode using local fixtures",
    )
    build_cmd.set_defaults(func=run_dataset_build)

    inspect_cmd = dataset_subparsers.add_parser(
        "inspect",
        help="Inspect dataset integrity and manifest",
    )
    inspect_cmd.add_argument(
        "dataset_id",
        help="Dataset identifier",
    )
    inspect_cmd.add_argument(
        "--verify-hash",
        action="store_true",
        default=False,
        help="Verify content hashes against manifest",
    )
    inspect_cmd.set_defaults(func=run_dataset_inspect)

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
