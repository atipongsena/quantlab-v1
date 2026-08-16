"""CLI command handlers for research report verification."""

from __future__ import annotations

import argparse

from quantlab.application.research import ResearchCampaignService


def run_report_verify(args: argparse.Namespace) -> int:
    service = ResearchCampaignService()
    report_path = getattr(args, "report_path", "artifacts/latest/research-report.json")

    passed, message = service.verify_report(report_path)

    print("=" * 70)
    print("QuantLab Cryptographic Research Report Verifier")
    print("=" * 70)
    print(f"Target Report : {report_path}")
    print(f"Status        : {'VERIFIED [PASS]' if passed else 'FAILED [REJECTED]'}")
    print(f"Details       : {message}")
    print("=" * 70)

    return 0 if passed else 1
