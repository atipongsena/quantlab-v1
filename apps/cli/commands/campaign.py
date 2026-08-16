"""CLI command handlers for multi-agent research campaigns."""

from __future__ import annotations

import argparse
import json

from quantlab.application.research import ResearchCampaignService


def run_campaign_run(args: argparse.Namespace) -> int:
    service = ResearchCampaignService()
    config_path = getattr(args, "config", "configs/campaigns/quality-improves-momentum-v1.yaml")

    report = service.run_campaign(config_path)

    if getattr(args, "output", "text") == "json":
        print(json.dumps(report.as_dict(), indent=2))
        return 0

    print("=" * 70)
    print("QuantLab Autonomous Multi-Agent Research Campaign")
    print("=" * 70)
    print(f"Report ID        : {report.report_id}")
    print(f"Campaign ID      : {report.campaign_id}")
    print(f"Generated At     : {report.generated_at}")
    print(f"Hypotheses Count : {report.hypotheses_count}")
    print("-" * 70)
    print("Hypothesis Verdicts:")
    for hyp_id, verdict in report.verdicts.items():
        print(f"  [{hyp_id}] : {verdict}")
    print("-" * 70)
    print(f"Content Hash     : {report.content_hash[:16]}...")
    print("=" * 70)
    print("Status: PASS [Research campaign completed successfully]")
    return 0
