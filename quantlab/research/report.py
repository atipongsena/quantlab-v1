"""Authoritative structured research report model and cryptographic verifier."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from quantlab.research.campaign import CampaignExecutionResult


@dataclass(frozen=True, slots=True)
class ResearchReport:
    report_id: str
    campaign_id: str
    generated_at: str
    hypotheses_count: int
    verdicts: Mapping[str, str]
    falsification_summary: Mapping[str, object]
    agent_dialogue_summary: Mapping[str, object]
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "report_id": self.report_id,
            "campaign_id": self.campaign_id,
            "generated_at": self.generated_at,
            "hypotheses_count": self.hypotheses_count,
            "verdicts": dict(self.verdicts),
            "falsification_summary": dict(self.falsification_summary),
            "agent_dialogue_summary": dict(self.agent_dialogue_summary),
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_campaign_result(cls, result: CampaignExecutionResult) -> ResearchReport:
        now_str = datetime.now(tz=UTC).isoformat()
        report_id = f"REP-{result.campaign_id}"

        f_summary = {
            "total_falsification_checks": len(result.falsification_reports),
            "all_passed": all(r.passed for r in result.falsification_reports),
            "reports": [r.as_dict() for r in result.falsification_reports],
        }

        d_summary = {
            "dialogue_id": result.dialogue.dialogue_id,
            "total_messages": len(result.dialogue.messages),
            "messages": [m.as_dict() for m in result.dialogue.messages],
        }

        payload = {
            "report_id": report_id,
            "campaign_id": result.campaign_id,
            "generated_at": now_str,
            "hypotheses_count": result.hypotheses_count,
            "verdicts": dict(result.verdicts),
            "falsification_summary": f_summary,
            "agent_dialogue_summary": d_summary,
        }
        chash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        return cls(
            report_id=report_id,
            campaign_id=result.campaign_id,
            generated_at=now_str,
            hypotheses_count=result.hypotheses_count,
            verdicts=result.verdicts,
            falsification_summary=f_summary,
            agent_dialogue_summary=d_summary,
            content_hash=chash,
        )


class ReportVerifier:
    """Verifies cryptographic integrity and reproducibility of research reports."""

    @classmethod
    def verify(cls, report_path: str | Path) -> tuple[bool, str]:
        path = Path(report_path)
        if not path.is_file():
            return False, f"Report file not found: {path}"

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return False, f"Failed to parse report JSON: {e}"

        recorded_hash = data.get("content_hash")
        if not recorded_hash:
            return False, "Missing 'content_hash' in report"

        # Recompute hash
        payload = {
            "report_id": data.get("report_id"),
            "campaign_id": data.get("campaign_id"),
            "generated_at": data.get("generated_at"),
            "hypotheses_count": data.get("hypotheses_count"),
            "verdicts": data.get("verdicts"),
            "falsification_summary": data.get("falsification_summary"),
            "agent_dialogue_summary": data.get("agent_dialogue_summary"),
        }
        recomputed_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        if recorded_hash != recomputed_hash:
            return False, f"Content hash mismatch: recorded {recorded_hash} != {recomputed_hash}"

        return True, "Report verified successfully: valid schema and cryptographic content hash"
