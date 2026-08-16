"""Time partition definitions and purged/embargoed boundary management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class PartitionType(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"  # Lockbox holdout partition


@dataclass(frozen=True, slots=True)
class TimePartition:
    """Disjoint chronological time interval with purge and embargo boundaries."""

    partition_id: str
    partition_type: PartitionType
    start_date: date
    end_date: date
    purge_days: int = 0
    embargo_days: int = 0

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError(
                f"start_date {self.start_date} must be on or before end_date {self.end_date}"
            )
        if self.purge_days < 0 or self.embargo_days < 0:
            raise ValueError("purge_days and embargo_days must be non-negative")

    def contains(self, target_date: date) -> bool:
        return self.start_date <= target_date <= self.end_date


@dataclass(frozen=True, slots=True)
class PartitionScheme:
    """Collection of time partitions validated for non-overlapping chronology."""

    partitions: tuple[TimePartition, ...]

    def __post_init__(self) -> None:
        sorted_parts = sorted(self.partitions, key=lambda p: p.start_date)
        for i in range(len(sorted_parts) - 1):
            cur = sorted_parts[i]
            nxt = sorted_parts[i + 1]
            if cur.end_date >= nxt.start_date:
                raise ValueError(
                    f"Partition overlap detected between '{cur.partition_id}' ({cur.end_date}) "
                    f"and '{nxt.partition_id}' ({nxt.start_date})"
                )

    def get_partition(self, partition_id: str) -> TimePartition | None:
        for p in self.partitions:
            if p.partition_id == partition_id:
                return p
        return None

    def get_by_type(self, partition_type: PartitionType) -> tuple[TimePartition, ...]:
        return tuple(p for p in self.partitions if p.partition_type == partition_type)
