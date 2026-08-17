"""CLI commands for factor research and composite strategies."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from quantlab.application.factor_research import FactorResearchService


def run_factor_list(args: argparse.Namespace) -> int:
    service = FactorResearchService()
    factors = service.list_factors()

    if getattr(args, "output", "text") == "json":
        print(json.dumps(factors, indent=2))
        return 0

    print("=" * 80)
    print(f"QuantLab V1 Factor Catalog ({len(factors)} Factors Registered)")
    print("=" * 80)
    for f in factors:
        direction_str = "+1 (Long High)" if f["direction"] == 1 else "-1 (Long Low)"
        print(f"Factor ID   : {f['factor_id']} (v{f['version']})")
        print(f"Name        : {f['name']} [{str(f['category']).upper()}]")
        print(f"Formula     : {f['formula']}")
        print(f"Direction   : {direction_str} | Lookback: {f['lookback_sessions']} sessions")
        print(f"Description : {f['description']}")
        print("-" * 80)

    return 0


def run_factor_research(args: argparse.Namespace) -> int:
    service = FactorResearchService()
    start_date = date.fromisoformat(args.start) if getattr(args, "start", None) else None
    end_date = date.fromisoformat(args.end) if getattr(args, "end", None) else None

    result = service.run_factor_research(
        factor_id=args.factor_id,
        dataset_id=args.dataset,
        start_date=start_date,
        end_date=end_date,
    )

    # Save evidence artifact to artifacts/latest/factor-research.json
    latest_dir = Path.cwd() / "artifacts" / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    with open(latest_dir / "factor-research.json", "w", encoding="utf-8") as f:
        json.dump(result.as_dict(), f, indent=2)

    if getattr(args, "output", "text") == "json":
        print(json.dumps(result.as_dict(), indent=2))
        return 0

    print("=" * 70)
    print(f"Factor Research Report: {result.factor_id}")
    print(
        f"Period: {result.start_session} to {result.end_session} ({result.num_sessions} sessions)"
    )
    print("=" * 70)
    print(f"Information Coefficient (IC) Mean : {result.ic_mean:+.4f}")
    print(f"IC Standard Deviation              : {result.ic_std:.4f}")
    print(f"Information Ratio (IR)             : {result.ic_ir:+.4f}")
    print(f"Positive IC Frequency              : {result.ic_positive_pct * 100:.1f}%")
    print(f"Rank IC (Spearman) Mean            : {result.rank_ic_mean:+.4f}")
    print(f"Rank IC IR                         : {result.rank_ic_ir:+.4f}")
    print("-" * 70)
    print("IC Decay Profile:")
    for horizon, ic_val in result.decay_profile.items():
        print(f"  - {horizon:>4}: {ic_val:+.4f}")
    print("-" * 70)
    print("Quantile Annualized Forward Returns:")
    for q_name, ret in sorted(result.quantile_returns.items()):
        print(f"  - {q_name:>4}: {ret * 100:+.2f}%")
    print(f"Spread (Q5 - Q1) : {result.spread_q5_minus_q1 * 100:+.2f}%")
    print(f"Coverage: {result.coverage_mean * 100:.1f}%")
    print(f"Turnover: {result.turnover_mean * 100:.1f}%")
    print(f"Status: [{result.diagnostic_label}]")
    print("=" * 70)

    return 0


def run_factor_composite(args: argparse.Namespace) -> int:
    service = FactorResearchService()
    start_date = date.fromisoformat(args.start) if getattr(args, "start", None) else None
    end_date = date.fromisoformat(args.end) if getattr(args, "end", None) else None

    result = service.run_composite(
        composite_id=args.composite_id,
        dataset_id=args.dataset,
        config_path=getattr(args, "config", None),
        start_date=start_date,
        end_date=end_date,
    )

    if getattr(args, "output", "text") == "json":
        print(json.dumps(result.as_dict(), indent=2))
        return 0

    print("=" * 70)
    print(f"Composite Strategy Report: {result.factor_id}")
    print(
        f"Period: {result.start_session} to {result.end_session} ({result.num_sessions} sessions)"
    )
    print("=" * 70)
    print(f"Composite IC Mean                  : {result.ic_mean:+.4f}")
    print(f"Composite IC IR                    : {result.ic_ir:+.4f}")
    print(f"Composite Rank IC Mean             : {result.rank_ic_mean:+.4f}")
    print(f"Composite Rank IC IR               : {result.rank_ic_ir:+.4f}")
    print("-" * 70)
    print("Quantile Annualized Returns:")
    for q_name, ret in sorted(result.quantile_returns.items()):
        print(f"  - {q_name:>4}: {ret * 100:+.2f}%")
    print(f"Spread (Q5 - Q1) : {result.spread_q5_minus_q1 * 100:+.2f}%")
    print(f"Status: [{result.diagnostic_label}]")
    print("=" * 70)

    return 0
