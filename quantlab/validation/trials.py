"""Append-only research trial ledger recording all backtest and validation attempts."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class TrialRecord:
    trial_id: str
    campaign_id: str
    candidate_id: str
    trial_spec: Mapping[str, object]
    spec_hash: str
    observed_sharpe: float
    observed_cagr: float
    recorded_at: datetime


class TrialLedger:
    """Immutable, append-only ledger preventing silent deletion of negative research trials."""

    def __init__(self) -> None:
        self._trials: list[TrialRecord] = []
        self._by_hash: dict[str, TrialRecord] = {}

    @property
    def total_trials(self) -> int:
        return len(self._trials)

    @property
    def records(self) -> tuple[TrialRecord, ...]:
        return tuple(self._trials)

    def record_once(
        self,
        campaign_id: str,
        candidate_id: str,
        trial_spec: Mapping[str, object],
        observed_sharpe: float,
        observed_cagr: float,
        recorded_at: datetime | None = None,
    ) -> TrialRecord:
        encoded = json.dumps(trial_spec, sort_keys=True).encode("utf-8")
        shash = hashlib.sha256(encoded).hexdigest()

        if shash in self._by_hash:
            return self._by_hash[shash]

        now = recorded_at or datetime.now(tz=UTC)
        record = TrialRecord(
            trial_id=f"TRL-{uuid.uuid4().hex[:12]}",
            campaign_id=campaign_id,
            candidate_id=candidate_id,
            trial_spec=trial_spec,
            spec_hash=shash,
            observed_sharpe=observed_sharpe,
            observed_cagr=observed_cagr,
            recorded_at=now,
        )
        self._trials.append(record)
        self._by_hash[shash] = record
        return record

    def get_sharpes_for_campaign(self, campaign_id: str) -> tuple[float, ...]:
        return tuple(t.observed_sharpe for t in self._trials if t.campaign_id == campaign_id)
