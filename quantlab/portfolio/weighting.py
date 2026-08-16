"""Portfolio asset weighting schemes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Protocol

from quantlab.domain.identity import InstrumentId
from quantlab.portfolio.selection import SelectedAsset


class WeightingScheme(Protocol):
    def compute_weights(
        self,
        selected_assets: Sequence[SelectedAsset],
        total_target_weight: Decimal = Decimal("1.0"),
        risk_metrics: Mapping[InstrumentId, float] | None = None,
    ) -> dict[InstrumentId, Decimal]: ...


class EqualWeighting:
    """Assigns equal weights to all selected assets summing to total_target_weight."""

    def compute_weights(
        self,
        selected_assets: Sequence[SelectedAsset],
        total_target_weight: Decimal = Decimal("1.0"),
        risk_metrics: Mapping[InstrumentId, float] | None = None,
    ) -> dict[InstrumentId, Decimal]:
        if not selected_assets:
            return {}

        n = Decimal(len(selected_assets))
        base_w = (total_target_weight / n).quantize(Decimal("0.000001"))

        weights: dict[InstrumentId, Decimal] = {}
        allocated = Decimal("0.0")

        # Assign base weights
        for asset in selected_assets:
            weights[asset.instrument_id] = base_w
            allocated += base_w

        # Distribute remaining dust to highest ranked asset deterministically
        dust = total_target_weight - allocated
        if dust != Decimal("0.0"):
            top_asset = selected_assets[0].instrument_id
            weights[top_asset] += dust

        return weights


class InverseVolatilityWeighting:
    """Assigns weights inversely proportional to realized volatility."""

    def compute_weights(
        self,
        selected_assets: Sequence[SelectedAsset],
        total_target_weight: Decimal = Decimal("1.0"),
        risk_metrics: Mapping[InstrumentId, float] | None = None,
    ) -> dict[InstrumentId, Decimal]:
        if not selected_assets:
            return {}

        metrics = risk_metrics or {}
        inv_vols: dict[InstrumentId, float] = {}

        for asset in selected_assets:
            vol = metrics.get(asset.instrument_id, 0.20)
            if vol <= 1e-4:
                vol = 0.20
            inv_vols[asset.instrument_id] = 1.0 / vol

        total_inv_vol = sum(inv_vols.values())
        if total_inv_vol <= 1e-12:
            return EqualWeighting().compute_weights(selected_assets, total_target_weight)

        weights: dict[InstrumentId, Decimal] = {}
        allocated = Decimal("0.0")

        for asset in selected_assets:
            inst = asset.instrument_id
            raw_fraction = Decimal(str(round(inv_vols[inst] / total_inv_vol, 6)))
            w = (total_target_weight * raw_fraction).quantize(Decimal("0.000001"))
            weights[inst] = w
            allocated += w

        dust = total_target_weight - allocated
        if dust != Decimal("0.0"):
            top_asset = selected_assets[0].instrument_id
            weights[top_asset] += dust

        return weights
