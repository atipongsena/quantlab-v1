"""Portfolio asset selection with hysteresis buffer rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from quantlab.domain.identity import InstrumentId


class SelectionReason(StrEnum):
    TOP_K_ENTRY = "top_k_entry"
    BUFFER_HOLD = "buffer_hold"
    FORCED_EXIT = "forced_exit"


@dataclass(frozen=True, slots=True)
class SelectedAsset:
    instrument_id: InstrumentId
    rank: int
    score: float
    reason: SelectionReason


class TopKBufferSelector:
    """Selects target assets using a Top-K entry and Top-B (buffer) hold policy.

    Parameters
    ----------
    target_size : int
        Target number of active positions (K, e.g. 30).
    buffer_size : int
        Maximum rank to retain existing holdings (B, e.g. 40, where B >= K).
    """

    def __init__(self, target_size: int = 30, buffer_size: int = 40) -> None:
        if target_size <= 0:
            raise ValueError(f"target_size must be positive, got {target_size}")
        if buffer_size < target_size:
            raise ValueError(f"buffer_size ({buffer_size}) must be >= target_size ({target_size})")
        self._target_size = target_size
        self._buffer_size = buffer_size

    @property
    def target_size(self) -> int:
        return self._target_size

    @property
    def buffer_size(self) -> int:
        return self._buffer_size

    def select(
        self,
        scores: Mapping[InstrumentId, float],
        current_holdings: Sequence[InstrumentId] = (),
    ) -> tuple[SelectedAsset, ...]:
        """Select assets from cross-sectional scores and current holdings.

        Ties are broken deterministically using the instrument UUID string.
        """
        if not scores:
            return ()

        # 1. Sort all candidates deterministically: descending score, ascending UUID
        sorted_candidates = sorted(
            scores.items(),
            key=lambda item: (-item[1], str(item[0].value)),
        )

        rank_map: dict[InstrumentId, int] = {
            inst_id: idx + 1 for idx, (inst_id, _) in enumerate(sorted_candidates)
        }
        score_map: dict[InstrumentId, float] = dict(sorted_candidates)

        current_set = set(current_holdings)
        selected: dict[InstrumentId, SelectedAsset] = {}

        # Step 1: Retain current holdings that remain within the buffer rank (rank <= buffer_size)
        for inst_id in sorted(current_set, key=lambda inst: rank_map.get(inst, 999999)):
            if inst_id in rank_map and len(selected) < self._target_size:
                rank = rank_map[inst_id]
                if rank <= self._buffer_size:
                    reason = (
                        SelectionReason.TOP_K_ENTRY
                        if rank <= self._target_size
                        else SelectionReason.BUFFER_HOLD
                    )
                    selected[inst_id] = SelectedAsset(
                        instrument_id=inst_id,
                        rank=rank,
                        score=score_map[inst_id],
                        reason=reason,
                    )

        # Step 2: Fill remaining capacity up to target_size from top-ranked candidates
        for inst_id, score in sorted_candidates:
            if len(selected) >= self._target_size:
                break
            if inst_id not in selected:
                rank = rank_map[inst_id]
                selected[inst_id] = SelectedAsset(
                    instrument_id=inst_id,
                    rank=rank,
                    score=score,
                    reason=SelectionReason.TOP_K_ENTRY,
                )

        # Return sorted by rank
        return tuple(sorted(selected.values(), key=lambda a: a.rank))
