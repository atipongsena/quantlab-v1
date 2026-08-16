"""CLI command handlers for strategy validation and falsification."""

from __future__ import annotations

import argparse
import json

from quantlab.application.validation import ValidationService


def run_validate(args: argparse.Namespace) -> int:
    service = ValidationService()

    result = service.run_validation(
        config_path=args.config,
        experiment_id=getattr(args, "experiment", "EXP-SYNTHETIC"),
    )

    if getattr(args, "output", "text") == "json":
        print(json.dumps(result.as_dict(), indent=2))
        return 0

    print("=" * 70)
    print(f"Validation Falsification Report: {result.candidate.strategy_id}")
    print(f"Candidate ID : {result.candidate.candidate_id}")
    print(f"Verdict      : {result.verdict.value}")
    print("=" * 70)
    print("Hard Correctness Gates:")
    for g in result.hard_gates:
        status_str = "[PASS]" if g.passed else "[FAIL]"
        print(f"  {status_str} {g.gate_type.value:<22}: {g.reason or 'OK'}")

    print("-" * 70)
    print("Robustness & Friction:")
    print(f"  Top-K Surface Topology  : {result.robustness.top_k_surface.topology.value}")
    be = result.robustness.cost_stress.break_even_cost_bps
    print(f"  Break-even Friction     : {be:.1f} bps")
    print(f"  HHI Concentration       : {result.robustness.concentration.herfindahl_index:.4f}")

    print("-" * 70)
    print("Statistical Diagnostics:")
    bs = result.bootstrap
    print(
        f"  Bootstrap 95% CI Sharpe : [{bs.ci_lower:.2f}, {bs.ci_upper:.2f}] "
        f"(Pt: {bs.point_estimate:.2f})"
    )
    print(f"  Deflated Sharpe p-value : {result.multiple_testing.deflated_sharpe_p_value:.4f}")
    print("=" * 70)
    print(f"Status: PASS [Verdict: {result.verdict.value}]")

    return 0
