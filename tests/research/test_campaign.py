"""Tests for multi-agent research campaign orchestrator."""

from pathlib import Path

from quantlab.research.campaign import CampaignOrchestrator


def test_campaign_orchestrator_execution() -> None:
    cfg_file = Path("configs/campaigns/quality-improves-momentum-v1.yaml")
    orchestrator = CampaignOrchestrator()

    res = orchestrator.run_campaign(cfg_file)

    assert res.campaign_id == "quality-improves-momentum-v1"
    assert res.hypotheses_count == 1
    assert "HYP-001" in res.verdicts
    assert res.verdicts["HYP-001"] == "VALIDATED"
    assert len(res.dialogue.messages) == 4  # 4 agent roles round-robin
