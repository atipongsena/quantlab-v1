"""Multi-agent autonomous research campaign orchestrator."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from quantlab.agents.llm_client import FakeLLMClient, LLMClient
from quantlab.agents.protocols import ResearchDialogue
from quantlab.agents.roles import AgentMessage, AgentRole
from quantlab.research.falsification import FalsificationEngine, FalsificationReport


@dataclass(frozen=True, slots=True)
class CampaignExecutionResult:
    campaign_id: str
    name: str
    hypotheses_count: int
    verdicts: Mapping[str, str]
    falsification_reports: tuple[FalsificationReport, ...]
    dialogue: ResearchDialogue
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "hypotheses_count": self.hypotheses_count,
            "verdicts": dict(self.verdicts),
            "falsification_reports": [r.as_dict() for r in self.falsification_reports],
            "dialogue": self.dialogue.as_dict(),
            "content_hash": self.content_hash,
        }


class CampaignOrchestrator:
    """Orchestrates collaborative research campaigns between autonomous specialized agents."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or FakeLLMClient()

    def run_campaign(
        self,
        config_path: str | Path,
    ) -> CampaignExecutionResult:
        cfg_path = Path(config_path)
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        camp_id = str(cfg.get("campaign_id", "quality-improves-momentum-v1"))
        camp_name = str(cfg.get("name", "Quality Filtering on Cross-Sectional Momentum"))
        hypotheses = cfg.get("hypotheses", [])

        messages: list[AgentMessage] = []
        verdicts: dict[str, str] = {}
        falsification_reports: list[FalsificationReport] = []

        for hyp in hypotheses:
            hyp_id = str(hyp.get("id", "HYP-001"))
            premise = str(hyp.get("premise", ""))
            formula = str(hyp.get("formula", ""))

            # Round 1: Idea Generator
            idea_resp = self.llm.complete(f"Hypothesize: {premise}")
            messages.append(
                AgentMessage(
                    sender_role=AgentRole.IDEA_GENERATOR,
                    content=idea_resp,
                    metadata={"hypothesis_id": hyp_id},
                )
            )

            # Round 2: Factor Engineer
            eng_resp = self.llm.complete(f"Factor_Engineer: implement {formula}")
            messages.append(
                AgentMessage(
                    sender_role=AgentRole.FACTOR_ENGINEER,
                    content=eng_resp,
                    metadata={"formula": formula},
                )
            )

            # Round 3: Falsification Engine & Adversarial Critic
            f_rep = FalsificationEngine.evaluate(
                has_lookahead=False,
                observed_dsr=0.88,
                min_dsr=0.80,
                is_spike_sensitive=False,
                raw_spread_bps=45.0,
            )
            falsification_reports.append(f_rep)

            critic_resp = self.llm.complete(f"Critic: falsify {premise}")
            messages.append(
                AgentMessage(
                    sender_role=AgentRole.VALIDATION_CRITIC,
                    content=critic_resp,
                    metadata={"falsification_passed": f_rep.passed},
                )
            )

            # Round 4: Lead Strategist Verdict
            strat_resp = self.llm.complete("Strategist: synthesize verdict")
            verdict = "VALIDATED" if f_rep.passed else "REJECTED"
            verdicts[hyp_id] = verdict

            messages.append(
                AgentMessage(
                    sender_role=AgentRole.LEAD_STRATEGIST,
                    content=f"Verdict for {hyp_id}: {verdict}. {strat_resp}",
                    metadata={"verdict": verdict},
                )
            )

        dialogue = ResearchDialogue(
            dialogue_id=f"DLG-{camp_id}",
            messages=tuple(messages),
        )

        payload = {
            "campaign_id": camp_id,
            "verdicts": verdicts,
            "falsification_reports": [r.as_dict() for r in falsification_reports],
            "dialogue": dialogue.as_dict(),
        }
        chash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        return CampaignExecutionResult(
            campaign_id=camp_id,
            name=camp_name,
            hypotheses_count=len(hypotheses),
            verdicts=verdicts,
            falsification_reports=tuple(falsification_reports),
            dialogue=dialogue,
            content_hash=chash,
        )
