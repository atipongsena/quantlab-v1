"""Candidate strategy freezing and immutable fingerprinting."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class FrozenCandidate:
    """Immutable, fingerprinted candidate strategy snapshot."""

    candidate_id: str
    strategy_id: str
    code_fingerprint: str
    strategy_config: Mapping[str, object]
    frozen_at: datetime
    config_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "code_fingerprint": self.code_fingerprint,
            "strategy_config": dict(self.strategy_config),
            "frozen_at": self.frozen_at.isoformat(),
            "config_hash": self.config_hash,
        }


class CandidateFreezer:
    """Freezes strategy configurations and assigns deterministic candidate identities."""

    @classmethod
    def freeze(
        cls,
        strategy_id: str,
        strategy_config: Mapping[str, object],
        code_fingerprint: str,
        frozen_at: datetime | None = None,
    ) -> FrozenCandidate:
        now = frozen_at or datetime.now(tz=UTC)
        encoded_cfg = json.dumps(strategy_config, sort_keys=True).encode("utf-8")
        cfg_hash = hashlib.sha256(encoded_cfg).hexdigest()

        # Candidate ID uniquely combines strategy_id and config hash
        candidate_id = f"CAND-{strategy_id}-{cfg_hash[:10]}"

        return FrozenCandidate(
            candidate_id=candidate_id,
            strategy_id=strategy_id,
            code_fingerprint=code_fingerprint,
            strategy_config=strategy_config,
            frozen_at=now,
            config_hash=cfg_hash,
        )
