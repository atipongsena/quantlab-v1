from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from quantlab.domain.identity import _require_nonempty, require_timezone_aware


class ValidationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    validation_id: str
    status: ValidationStatus
    created_at: datetime
    subject_id: str
    summary: str

    def __post_init__(self) -> None:
        _require_nonempty(self.validation_id, "validation_id")
        if not isinstance(self.status, ValidationStatus):
            raise TypeError("status must be ValidationStatus")
        require_timezone_aware(self.created_at, "created_at")
        _require_nonempty(self.subject_id, "subject_id")
        _require_nonempty(self.summary, "summary")
