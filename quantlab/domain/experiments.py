from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from quantlab.domain.identity import _require_nonempty, require_decimal, require_timezone_aware


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    LOCKED = "locked"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class Experiment:
    experiment_id: str
    status: ExperimentStatus
    created_at: datetime
    config_hash: str
    dataset_id: str

    def __post_init__(self) -> None:
        _require_nonempty(self.experiment_id, "experiment_id")
        if not isinstance(self.status, ExperimentStatus):
            raise TypeError("status must be ExperimentStatus")
        require_timezone_aware(self.created_at, "created_at")
        _require_nonempty(self.config_hash, "config_hash")
        _require_nonempty(self.dataset_id, "dataset_id")


@dataclass(frozen=True, slots=True)
class BacktestResult:
    result_id: str
    experiment_id: str
    created_at: datetime
    equity_curve_hash: str
    annual_return: Decimal
    max_drawdown: Decimal

    def __post_init__(self) -> None:
        _require_nonempty(self.result_id, "result_id")
        _require_nonempty(self.experiment_id, "experiment_id")
        require_timezone_aware(self.created_at, "created_at")
        _require_nonempty(self.equity_curve_hash, "equity_curve_hash")
        require_decimal(self.annual_return, "annual_return")
        require_decimal(self.max_drawdown, "max_drawdown")
