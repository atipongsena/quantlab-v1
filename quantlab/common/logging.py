from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from quantlab.common.clock import require_utc
from quantlab.common.config import JsonValue, redact_secrets


@dataclass(frozen=True, slots=True)
class StructuredLogEvent:
    message: str
    occurred_at: datetime
    correlation_id: str
    domain_ids: dict[str, str]
    level: str
    attributes: JsonValue

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "message": self.message,
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": self.correlation_id,
            "domain_ids": dict(sorted(self.domain_ids.items())),
            "level": self.level,
            "attributes": self.attributes,
        }


def build_log_event(
    *,
    message: str,
    occurred_at: datetime,
    correlation_id: str,
    domain_ids: dict[str, str],
    level: str,
    attributes: JsonValue,
) -> StructuredLogEvent:
    if not message:
        raise ValueError("message must be nonempty")
    require_utc(occurred_at)
    if not correlation_id:
        raise ValueError("correlation_id must be nonempty")
    if not domain_ids:
        raise ValueError("domain_ids must not be empty")
    if not level:
        raise ValueError("level must be nonempty")
    return StructuredLogEvent(
        message=message,
        occurred_at=occurred_at,
        correlation_id=correlation_id,
        domain_ids=dict(sorted(domain_ids.items())),
        level=level,
        attributes=redact_secrets(attributes),
    )
