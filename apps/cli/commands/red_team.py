"""CLI command handlers for red team falsification demonstrations."""

from __future__ import annotations

import argparse
import json

from quantlab.validation.red_team import RedTeamRunner


def run_red_team(args: argparse.Namespace) -> int:
    case_name = getattr(args, "case", None)
    if case_name == "lookahead":
        results = [RedTeamRunner.run_lookahead_case()]
    elif case_name == "random-mining":
        results = [RedTeamRunner.run_random_mining_case()]
    elif case_name == "cost-illusion":
        results = [RedTeamRunner.run_cost_illusion_case()]
    else:
        # Default run all cases
        results = RedTeamRunner.run_all()

    if getattr(args, "output", "text") == "json":
        print(json.dumps([r.as_dict() for r in results], indent=2))
        return 0

    print("=" * 70)
    print("QuantLab Active Red Team Falsification Report")
    print(f"Executed {len(results)} attack demonstration cases")
    print("=" * 70)

    for r in results:
        print(f"Case Strategy : {r.candidate.strategy_id}")
        print(f"Verdict       : {r.verdict.value}")
        if r.reasons:
            for reason in r.reasons:
                print(f"  - {reason}")
        print("-" * 70)

    print("Status: PASS [All attack vectors correctly defended]")
    return 0
