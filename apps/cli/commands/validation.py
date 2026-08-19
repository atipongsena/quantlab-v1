"""CLI command handlers for strategy validation and falsification."""

from __future__ import annotations

import argparse
import json
from datetime import date

from quantlab.application.validation import ValidationService


def run_validate(args: argparse.Namespace) -> int:
    service = ValidationService()

    result = service.run_validation(
        config_path=args.config,
        experiment_id=getattr(args, "experiment", "EXP-US-PRICE-COMPOSITE"),
        strategy_config_path=getattr(
            args, "strategy", "configs/strategies/us-price-composite-v1.yaml"
        ),
        dataset_id=getattr(args, "dataset", "DATASET-US-30Y-v001"),
        start_date=date.fromisoformat(args.start) if getattr(args, "start", None) else None,
        end_date=date.fromisoformat(args.end) if getattr(args, "end", None) else None,
        run_sweeps=not getattr(args, "no_sweeps", False),
    )

    if getattr(args, "output", "text") == "json":
        print(json.dumps(result.as_dict(), indent=2))
        return 0

    robustness = result.robustness
    print("=" * 70)
    print(f"Falsification report: {result.candidate.strategy_id}")
    print(f"Candidate : {result.candidate.candidate_id}")
    print(f"Verdict   : {result.verdict.value}")
    print("=" * 70)
    print("Hard correctness gates")
    for gate in result.hard_gates:
        marker = "pass" if gate.passed else "FAIL"
        print(f"  {marker:<5} {gate.gate_type.value:<22} {gate.reason or ''}")

    print("-" * 70)
    print(f"Portfolio size sweep ({robustness.top_k_surface.topology.value})")
    for cell in robustness.top_k_surface.cells:
        print(
            f"  top {str(cell.parameters.get('top_k')):<4} "
            f"Sharpe {cell.sharpe_ratio:+.2f}  CAGR {cell.cagr * 100:+.2f}%  "
            f"maxDD {cell.max_drawdown * 100:.2f}%"
        )

    if robustness.ablations:
        print("-" * 70)
        print("Factor ablations (composite renormalized without each sleeve)")
        for record in robustness.ablations:
            print(
                f"  without {record.omitted_factor:<20} Sharpe {record.sharpe_ratio:+.2f}  "
                f"contribution {record.marginal_contribution_sharpe:+.2f}"
            )

    if robustness.subperiod_cagr:
        print("-" * 70)
        print("Return by calendar year")
        years = list(robustness.subperiod_cagr.items())
        for i in range(0, len(years), 4):
            chunk = years[i : i + 4]
            print("  " + "   ".join(f"{y}: {v * 100:+6.1f}%" for y, v in chunk))

    print("-" * 70)
    print("Friction and concentration")
    stress = robustness.cost_stress
    print(f"  Break-even cost   : {stress.break_even_cost_bps:.1f} bps round trip")
    print(f"  Cost fragile      : {'yes' if stress.is_cost_fragile else 'no'}")
    print(f"  Herfindahl index  : {robustness.concentration.herfindahl_index:.4f}")

    print("-" * 70)
    print("Statistical diagnostics")
    bootstrap = result.bootstrap
    print(
        f"  Sharpe            : {bootstrap.point_estimate:+.2f} "
        f"(95% CI {bootstrap.ci_lower:+.2f} to {bootstrap.ci_upper:+.2f}, "
        f"stationary block bootstrap)"
    )
    testing = result.multiple_testing
    print(f"  Trials recorded   : {testing.n_trials}")
    print(
        f"  Return skew       : {testing.skewness:+.2f}  "
        f"excess kurtosis {testing.excess_kurtosis:+.2f}"
    )
    print(f"  Deflated Sharpe p : {testing.deflated_sharpe_p_value:.4f}")

    print("-" * 70)
    for reason in result.reasons:
        print(f"  - {reason}")
    print("=" * 70)
    return 0
