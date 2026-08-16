"""Factor snapshot creation, verification, and persistence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorSnapshot, FactorValue, MissingReason


def build_factor_snapshot(
    factor_id: str,
    version: str,
    session: date,
    as_of: datetime,
    raw_values: Mapping[InstrumentId, float | None | FactorValue],
    universe: Sequence[InstrumentId] | None = None,
    metadata: Mapping[str, object] | None = None,
) -> FactorSnapshot:
    """Build a deterministic, order-invariant factor snapshot."""
    target_universe = universe if universe is not None else list(raw_values.keys())
    values: dict[InstrumentId, FactorValue] = {}

    for inst_id in target_universe:
        raw = raw_values.get(inst_id)
        if raw is None:
            values[inst_id] = FactorValue(
                instrument_id=inst_id,
                value=None,
                missing_reason=MissingReason.NOT_IN_UNIVERSE
                if inst_id not in raw_values
                else MissingReason.INSUFFICIENT_HISTORY,
            )
        elif isinstance(raw, FactorValue):
            values[inst_id] = raw
        else:
            values[inst_id] = FactorValue(
                instrument_id=inst_id,
                value=float(raw),
                missing_reason=None,
            )

    return FactorSnapshot.create(
        factor_id=factor_id,
        version=version,
        session=session,
        as_of=as_of,
        values=values,
        metadata=metadata or {},
    )


def compute_composite_availability(
    snapshots: Sequence[FactorSnapshot],
) -> datetime:
    """Composite factor availability is the maximum available_at across all inputs."""
    if not snapshots:
        raise ValueError("Cannot compute availability of empty snapshots sequence")
    return max(snapshot.as_of for snapshot in snapshots)
