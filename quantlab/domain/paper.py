from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from quantlab.domain.identity import _require_nonempty, require_timezone_aware


class PaperDeploymentStatus(StrEnum):
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class PaperDeployment:
    deployment_id: str
    status: PaperDeploymentStatus
    created_at: datetime
    experiment_id: str
    broker_account_ref: str

    def __post_init__(self) -> None:
        _require_nonempty(self.deployment_id, "deployment_id")
        if not isinstance(self.status, PaperDeploymentStatus):
            raise TypeError("status must be PaperDeploymentStatus")
        require_timezone_aware(self.created_at, "created_at")
        _require_nonempty(self.experiment_id, "experiment_id")
        _require_nonempty(self.broker_account_ref, "broker_account_ref")
