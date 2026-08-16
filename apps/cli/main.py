from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from apps.cli.commands.backtest import run_backtest
from apps.cli.commands.factor import (
    run_factor_composite,
    run_factor_list,
    run_factor_research,
)
from apps.cli.commands.model import run_model_compare
from apps.cli.commands.paper import run_paper_reconcile, run_paper_run
from apps.cli.commands.red_team import run_red_team
from apps.cli.commands.validation import run_validate
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

    # factor
    factor_parser = subparsers.add_parser(
        "factor",
        help="Factor research and composite strategies",
    )
    factor_subparsers = factor_parser.add_subparsers(dest="factor_command", help="Factor actions")

    factor_list_cmd = factor_subparsers.add_parser(
        "list",
        help="List all registered factors in catalog",
    )
    factor_list_cmd.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    factor_list_cmd.set_defaults(func=run_factor_list)

    factor_res_cmd = factor_subparsers.add_parser(
        "research",
        help="Run factor research and IC evaluation",
    )
    factor_res_cmd.add_argument(
        "factor_id",
        help="Factor identifier (e.g. momentum_12_1, roe)",
    )
    factor_res_cmd.add_argument(
        "--dataset",
        required=True,
        help="Dataset identifier (e.g. DATASET-v001)",
    )
    factor_res_cmd.add_argument(
        "--start",
        help="Start date YYYY-MM-DD",
    )
    factor_res_cmd.add_argument(
        "--end",
        help="End date YYYY-MM-DD",
    )
    factor_res_cmd.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    factor_res_cmd.set_defaults(func=run_factor_research)

    factor_comp_cmd = factor_subparsers.add_parser(
        "composite",
        help="Evaluate multi-factor composite strategy",
    )
    factor_comp_cmd.add_argument(
        "composite_id",
        help="Composite model identifier (e.g. composite-v1)",
    )
    factor_comp_cmd.add_argument(
        "--dataset",
        required=True,
        help="Dataset identifier (e.g. DATASET-v001)",
    )
    factor_comp_cmd.add_argument(
        "--config",
        help="Path to composite config YAML",
    )
    factor_comp_cmd.add_argument(
        "--start",
        help="Start date YYYY-MM-DD",
    )
    factor_comp_cmd.add_argument(
        "--end",
        help="End date YYYY-MM-DD",
    )
    factor_comp_cmd.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    factor_comp_cmd.set_defaults(func=run_factor_composite)

    # Backtest subcommand
    backtest_parser = subparsers.add_parser(
        "backtest", help="Simulation and backtest engine commands"
    )
    backtest_subparsers = backtest_parser.add_subparsers(dest="backtest_command", required=True)

    backtest_run_cmd = backtest_subparsers.add_parser(
        "run", help="Run strategy backtest simulation"
    )
    backtest_run_cmd.add_argument(
        "config",
        help="Path to strategy config YAML (e.g. configs/strategies/composite-top30-v1.yaml)",
    )
    backtest_run_cmd.add_argument("--dataset", default="DATASET-v001", help="Dataset identifier")
    backtest_run_cmd.add_argument(
        "--offline", action="store_true", help="Run in strict offline mode"
    )
    backtest_run_cmd.add_argument("--start", help="Start date YYYY-MM-DD")
    backtest_run_cmd.add_argument("--end", help="End date YYYY-MM-DD")
    backtest_run_cmd.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format"
    )
    backtest_run_cmd.set_defaults(func=run_backtest)

    # Validation subcommand
    validate_parser = subparsers.add_parser(
        "validate", help="Validation and overfitting defense commands"
    )
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command", required=True)

    validate_run_cmd = validate_subparsers.add_parser(
        "run", help="Run strategy validation and falsification"
    )
    validate_run_cmd.add_argument(
        "config",
        help="Path to validation config YAML (e.g. configs/validation/default-v1.yaml)",
    )
    validate_run_cmd.add_argument(
        "--experiment", default="EXP-SYNTHETIC", help="Experiment identifier"
    )
    validate_run_cmd.add_argument(
        "--offline", action="store_true", help="Run in strict offline mode"
    )
    validate_run_cmd.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format"
    )
    validate_run_cmd.set_defaults(func=run_validate)

    # Red-team subcommand
    red_team_parser = subparsers.add_parser(
        "red-team", help="Active red teaming and falsification demonstrations"
    )
    red_team_subparsers = red_team_parser.add_subparsers(dest="red_team_command", required=True)

    red_team_run_cmd = red_team_subparsers.add_parser(
        "run", help="Run red team falsification attack cases"
    )
    red_team_run_cmd.add_argument(
        "--all", action="store_true", help="Run all red team demonstration cases"
    )
    red_team_run_cmd.add_argument(
        "--case",
        choices=["lookahead", "random-mining", "cost-illusion"],
        help="Run specific attack case",
    )
    red_team_run_cmd.add_argument("--dataset", default="DATASET-v001", help="Dataset identifier")
    red_team_run_cmd.set_defaults(func=run_red_team)

    # Model subcommand
    model_parser = subparsers.add_parser("model", help="Machine learning model comparison commands")
    model_subparsers = model_parser.add_subparsers(dest="model_command", required=True)

    model_compare_cmd = model_subparsers.add_parser(
        "compare", help="Compare heuristic and ML ranking models across walk-forward folds"
    )
    model_compare_cmd.add_argument("--dataset", default="DATASET-v001", help="Dataset identifier")
    model_compare_cmd.add_argument(
        "--walk-forward",
        default="configs/ml/walk-forward-v1.yaml",
        help="Path to walk-forward config YAML",
    )
    model_compare_cmd.add_argument(
        "--models",
        default="composite,ridge,lightgbm",
        help="Comma-separated model names to compare",
    )
    model_compare_cmd.add_argument(
        "--offline", action="store_true", help="Run in strict offline mode"
    )
    model_compare_cmd.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format"
    )
    model_compare_cmd.set_defaults(func=run_model_compare)

    # Paper trading subcommand
    paper_parser = subparsers.add_parser(
        "paper", help="Paper trading operational lifecycle and reconciliation commands"
    )
    paper_subparsers = paper_parser.add_subparsers(dest="paper_command", required=True)

    paper_run_cmd = paper_subparsers.add_parser("run", help="Execute daily paper trading cycle")
    paper_run_cmd.add_argument("--date", default="2026-01-05", help="Session date (YYYY-MM-DD)")
    paper_run_cmd.add_argument(
        "--strategy",
        default="configs/strategies/composite-top30-v1.yaml",
        help="Path to strategy config YAML",
    )
    paper_run_cmd.add_argument("--offline", action="store_true", help="Run in strict offline mode")
    paper_run_cmd.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format"
    )
    paper_run_cmd.set_defaults(func=run_paper_run)

    paper_reconcile_cmd = paper_subparsers.add_parser(
        "reconcile", help="Reconcile shadow ledger with broker account"
    )
    paper_reconcile_cmd.add_argument(
        "--date", default="2026-01-05", help="Session date (YYYY-MM-DD)"
    )
    paper_reconcile_cmd.add_argument(
        "--strategy",
        default="configs/strategies/composite-top30-v1.yaml",
        help="Path to strategy config YAML",
    )
    paper_reconcile_cmd.add_argument(
        "--offline", action="store_true", help="Run in strict offline mode"
    )
    paper_reconcile_cmd.add_argument(
        "--output", choices=["text", "json"], default="text", help="Output format"
    )
    paper_reconcile_cmd.set_defaults(func=run_paper_reconcile)

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
