"""Application service for research campaign lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

from quantlab.agents.llm_client import FakeLLMClient, LLMClient
from quantlab.research.campaign import CampaignOrchestrator
from quantlab.research.report import ReportVerifier, ResearchReport


class ResearchCampaignService:
    """Coordinates autonomous multi-agent research campaigns and reports."""

    def __init__(self, base_dir: Path | None = None, llm_client: LLMClient | None = None) -> None:
        self._base_dir = base_dir or Path.cwd()
        self._llm = llm_client or FakeLLMClient()

    def run_campaign(
        self,
        config_path: str | Path,
        output_path: Path | None = None,
    ) -> ResearchReport:
        orchestrator = CampaignOrchestrator(llm_client=self._llm)
        cfg_file = Path(config_path)
        if not cfg_file.is_absolute():
            cfg_file = self._base_dir / cfg_file

        result = orchestrator.run_campaign(cfg_file)
        report = ResearchReport.from_campaign_result(result)

        out_file = output_path or self._base_dir / "artifacts" / "latest" / "research-report.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report.as_dict(), f, indent=2)

        return report

    def verify_report(self, report_path: str | Path) -> tuple[bool, str]:
        path = Path(report_path)
        if not path.is_absolute():
            path = self._base_dir / path
        return ReportVerifier.verify(path)
