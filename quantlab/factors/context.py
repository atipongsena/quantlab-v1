"""Factor execution context and boundary rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime

from quantlab.data.pit_facade import PointInTimeData
from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorContext


def create_factor_context(
    dataset_id: str,
    session: date,
    as_of: datetime,
    pit_data: PointInTimeData,
    universe: Sequence[InstrumentId],
    parameters: Mapping[str, object] | None = None,
) -> FactorContext:
    """Create a point-in-time factor execution context."""
    return FactorContext(
        dataset_id=dataset_id,
        session=session,
        as_of=as_of,
        pit_data=pit_data,
        universe=tuple(universe),
        parameters=parameters or {},
    )
