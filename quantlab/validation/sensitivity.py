"""Parameter sensitivity grid analysis and plateau/spike classification."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum


class ParameterTopology(StrEnum):
    PLATEAU = "plateau"
    SPIKE = "spike"
    MONOTONIC = "monotonic"
    FRAGILE = "fragile"


@dataclass(frozen=True, slots=True)
class SensitivityCell:
    parameters: Mapping[str, object]
    sharpe_ratio: float
    cagr: float
    max_drawdown: float


@dataclass(frozen=True, slots=True)
class SensitivitySurface:
    parameter_name: str
    cells: tuple[SensitivityCell, ...]
    topology: ParameterTopology

    @classmethod
    def analyze(
        cls,
        parameter_name: str,
        cells: Sequence[SensitivityCell],
    ) -> SensitivitySurface:
        if len(cells) < 2:
            return cls(
                parameter_name=parameter_name,
                cells=tuple(cells),
                topology=ParameterTopology.PLATEAU,
            )

        sharpes = [c.sharpe_ratio for c in cells]
        mean_sharpe = sum(sharpes) / len(sharpes)
        max_sharpe = max(sharpes)
        min_sharpe = min(sharpes)

        # Spike detection: peak is > 1.5x surrounding mean and difference is large
        if max_sharpe > 1.5 * mean_sharpe and (max_sharpe - min_sharpe) > 0.75:
            topology = ParameterTopology.SPIKE
        elif max_sharpe - min_sharpe < 0.35:
            topology = ParameterTopology.PLATEAU
        elif all(sharpes[i] >= sharpes[i + 1] for i in range(len(sharpes) - 1)) or all(
            sharpes[i] <= sharpes[i + 1] for i in range(len(sharpes) - 1)
        ):
            topology = ParameterTopology.MONOTONIC
        else:
            topology = ParameterTopology.FRAGILE

        return cls(
            parameter_name=parameter_name,
            cells=tuple(cells),
            topology=topology,
        )
