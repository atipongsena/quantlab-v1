"""Machine learning contracts, tabular datasets, and label specifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from quantlab.domain.identity import InstrumentId


class LabelType(StrEnum):
    FORWARD_RETURN = "forward_return"
    CROSS_SECTIONAL_EXCESS = "cross_sectional_excess"
    CROSS_SECTIONAL_RANK = "cross_sectional_rank"


@dataclass(frozen=True, slots=True)
class LabelSpec:
    horizon_sessions: int = 21
    label_type: LabelType = LabelType.CROSS_SECTIONAL_EXCESS
    winsorize_limits: tuple[float, float] = (0.01, 0.01)


@dataclass(frozen=True, slots=True)
class MLFeatureRow:
    session: date
    instrument_id: InstrumentId
    features: tuple[float, ...]
    label: float | None = None


@dataclass(frozen=True, slots=True)
class MLDataset:
    dataset_id: str
    feature_names: tuple[str, ...]
    rows: tuple[MLFeatureRow, ...]

    @property
    def sessions(self) -> tuple[date, ...]:
        return tuple(sorted({r.session for r in self.rows}))

    @property
    def instruments(self) -> tuple[InstrumentId, ...]:
        return tuple(sorted({r.instrument_id for r in self.rows}, key=lambda x: str(x.value)))

    def get_by_session(self, session: date) -> tuple[MLFeatureRow, ...]:
        return tuple(r for r in self.rows if r.session == session)

    def filter_by_date_range(self, start_date: date, end_date: date) -> MLDataset:
        filtered = tuple(r for r in self.rows if start_date <= r.session <= end_date)
        return MLDataset(
            dataset_id=f"{self.dataset_id}-filtered",
            feature_names=self.feature_names,
            rows=filtered,
        )
