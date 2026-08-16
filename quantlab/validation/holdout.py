"""Lockbox holdout ledger and access control service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class HoldoutStatus(StrEnum):
    UNTOUCHED = "untouched"
    CONSUMED = "consumed"


@dataclass(frozen=True, slots=True)
class HoldoutAccess:
    """Audit record for accessing a holdout partition."""

    access_id: str
    candidate_id: str
    partition_id: str
    actor: str
    purpose: str
    accessed_at: datetime


class HoldoutService:
    """Manages one-way irreversible consumption of test lockbox holdouts."""

    def __init__(self) -> None:
        self._consumed_holdouts: dict[tuple[str, str], HoldoutAccess] = {}

    def is_consumed(self, candidate_id: str, partition_id: str) -> bool:
        return (candidate_id, partition_id) in self._consumed_holdouts

    def open_holdout(
        self,
        candidate_id: str,
        partition_id: str,
        actor: str,
        purpose: str,
        accessed_at: datetime | None = None,
    ) -> HoldoutAccess:
        key = (candidate_id, partition_id)
        if key in self._consumed_holdouts:
            existing = self._consumed_holdouts[key]
            # Access is already recorded and consumed
            return existing

        now = accessed_at or datetime.now(tz=UTC)
        access = HoldoutAccess(
            access_id=f"HLD-{uuid.uuid4().hex[:12]}",
            candidate_id=candidate_id,
            partition_id=partition_id,
            actor=actor,
            purpose=purpose,
            accessed_at=now,
        )
        self._consumed_holdouts[key] = access
        return access

    def get_access_history(self, candidate_id: str) -> tuple[HoldoutAccess, ...]:
        return tuple(
            access for (cand, _), access in self._consumed_holdouts.items() if cand == candidate_id
        )
