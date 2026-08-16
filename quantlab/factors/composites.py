"""Composite factor models combining normalized multi-factor snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorSnapshot, FactorValue, MissingReason
from quantlab.factors.snapshots import build_factor_snapshot, compute_composite_availability
from quantlab.factors.transforms import TransformSpec, transform_cross_section


@dataclass(frozen=True, slots=True)
class CompositeSpec:
    """Specification for multi-factor linear composite scoring."""

    composite_id: str
    version: str
    factor_weights: Mapping[str, float]
    min_weight_fraction: float = 0.5
    normalize_method: str = "zscore"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.factor_weights:
            raise ValueError("Composite factor_weights cannot be empty")
        total_w = sum(self.factor_weights.values())
        if abs(total_w - 1.0) > 1e-3:
            raise ValueError(f"Composite factor weights must sum to 1.0 (got {total_w:.4f})")


class CompositeBuilder:
    """Combines factor snapshots into a single deterministic composite snapshot."""

    @staticmethod
    def build(
        snapshots: Mapping[str, FactorSnapshot],
        spec: CompositeSpec,
        sector_map: Mapping[InstrumentId, str] | None = None,
    ) -> FactorSnapshot:
        if not snapshots:
            raise ValueError("Snapshots mapping cannot be empty")

        # Verify all requested factors are provided
        for factor_id in spec.factor_weights:
            if factor_id not in snapshots:
                raise ValueError(f"Missing required factor snapshot for composite: '{factor_id}'")

        # Ensure consistent session, as_of, universe across input snapshots
        first_snap = next(iter(snapshots.values()))
        session = first_snap.session
        universe = list(first_snap.values.keys())

        for fid, snap in snapshots.items():
            if snap.session != session:
                raise ValueError(
                    f"Mismatched session for factor '{fid}': {snap.session} vs {session}"
                )

        composite_as_of = compute_composite_availability(list(snapshots.values()))
        t_spec = TransformSpec(winsorize=True, zscore=True)

        # 1. Transform each factor cross-section (zscore normalized)
        normalized_scores: dict[str, dict[InstrumentId, float]] = {}
        for fid, weight in spec.factor_weights.items():
            snap = snapshots[fid]
            raw_scores = snap.valid_scores()
            norm_fv = transform_cross_section(raw_scores, t_spec)
            normalized_scores[fid] = {
                inst: fv.value for inst, fv in norm_fv.items() if fv.value is not None
            }

        # 2. Combine weights per instrument
        raw_composite: dict[InstrumentId, float] = {}
        composite_values: dict[InstrumentId, FactorValue] = {}

        for inst_id in universe:
            weighted_sum = 0.0
            weight_used = 0.0

            for fid, weight in spec.factor_weights.items():
                if inst_id in normalized_scores[fid]:
                    weighted_sum += weight * normalized_scores[fid][inst_id]
                    weight_used += weight

            if weight_used >= spec.min_weight_fraction:
                score = weighted_sum / weight_used
                raw_composite[inst_id] = score
                composite_values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=score,
                    missing_reason=None,
                )
            else:
                composite_values[inst_id] = FactorValue(
                    instrument_id=inst_id,
                    value=None,
                    missing_reason=MissingReason.INSUFFICIENT_HISTORY,
                )

        # 3. Final cross-sectional normalization on valid composite scores
        final_norm_fv = transform_cross_section(raw_composite, t_spec)
        for inst_id, fv in final_norm_fv.items():
            composite_values[inst_id] = FactorValue(
                instrument_id=inst_id,
                value=fv.value,
                missing_reason=fv.missing_reason,
            )

        return build_factor_snapshot(
            factor_id=spec.composite_id,
            version=spec.version,
            session=session,
            as_of=composite_as_of,
            raw_values=composite_values,
            universe=universe,
        )
