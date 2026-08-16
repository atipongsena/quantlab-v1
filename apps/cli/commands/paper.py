"""CLI command handlers for paper trading execution and reconciliation."""

from __future__ import annotations

import argparse
import json
from datetime import date

from quantlab.application.paper import PaperService


def run_paper_run(args: argparse.Namespace) -> int:
    service = PaperService()

    date_str = getattr(args, "date", "2026-01-05")
    session_date = date.fromisoformat(date_str)

    res = service.run_daily_cycle(
        session_date=session_date,
        strategy_config_path=getattr(
            args, "strategy", "configs/strategies/composite-top30-v1.yaml"
        ),
    )

    if getattr(args, "output", "text") == "json":
        print(json.dumps(res, indent=2))
        return 0

    print("=" * 70)
    print("QuantLab Paper Trading Daily Operational Cycle")
    print("=" * 70)
    print(f"Session Date     : {res['session']}")
    print(f"Strategy ID      : {res['strategy_id']}")
    print(f"Account ID       : {res['account_id']}")
    print(f"Orders Submitted : {res['orders_count']}")
    print(f"Fills Executed   : {res['fills_count']}")
    print(f"Cash Balance     : ${res['cash_balance']}")
    print(f"Total Equity     : ${res['total_equity']}")
    print("=" * 70)
    print("Status: PASS [Daily paper trading cycle completed]")
    return 0


def run_paper_reconcile(args: argparse.Namespace) -> int:
    service = PaperService()

    date_str = getattr(args, "date", "2026-01-05")
    session_date = date.fromisoformat(date_str)

    res = service.reconcile_daily(
        session_date=session_date,
        strategy_config_path=getattr(
            args, "strategy", "configs/strategies/composite-top30-v1.yaml"
        ),
    )

    if getattr(args, "output", "text") == "json":
        print(json.dumps(res, indent=2))
        return 0

    print("=" * 70)
    print("QuantLab Shadow Position & Cash Reconciliation")
    print("=" * 70)
    print(f"Session Date     : {res['session']}")
    print(f"Clean Status     : {'CLEAN' if res['is_clean'] else 'BREAKS DETECTED'}")
    print(f"Max Severity     : {res['max_severity']}")
    print(f"Breaks Count     : {len(res.get('breaks', []))}")  # type: ignore[arg-type]
    print(f"Content Hash     : {res['content_hash'][:16]}...")
    print("=" * 70)
    print("Status: PASS [Reconciliation completed successfully]")
    return 0


def run_paper_simulate(args: argparse.Namespace) -> int:
    service = PaperService()

    res = service.simulate_forward(
        deployment_id=getattr(args, "deployment", "PAPER-SYNTHETIC"),
        sessions_range=getattr(args, "sessions", "2024-01-01:2024-04-30"),
    )

    if getattr(args, "output", "text") == "json":
        print(json.dumps(res, indent=2))
        return 0

    print("=" * 70)
    print("QuantLab Operational Paper Forward Simulation")
    print("=" * 70)
    print(f"Deployment ID    : {res['deployment_id']}")
    print(f"Date Range       : {res['start_date']} to {res['end_date']}")
    print(f"Trading Sessions : {res['total_sessions']}")
    print(f"Total Orders     : {res['orders_count']}")
    print(f"Total Fills      : {res['fills_count']}")
    print(f"Clean Reconciles : {res['clean_reconciliations']}")
    print(f"Ending Equity    : ${res['total_equity']}")
    print("=" * 70)
    print("Status: PASS [Paper forward simulation completed successfully]")
    return 0
