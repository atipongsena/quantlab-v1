"""Tests for time partition boundary and chronological validation."""

from datetime import date

import pytest

from quantlab.validation.partitions import PartitionScheme, PartitionType, TimePartition


def test_partition_scheme_valid_chronology() -> None:
    p1 = TimePartition("P1", PartitionType.TRAIN, date(2015, 1, 1), date(2020, 12, 31))
    p2 = TimePartition("P2", PartitionType.VALIDATION, date(2021, 1, 1), date(2023, 12, 31))
    p3 = TimePartition("P3", PartitionType.TEST, date(2024, 1, 1), date(2025, 12, 31))

    scheme = PartitionScheme((p1, p2, p3))
    assert scheme.get_partition("P1") == p1
    assert len(scheme.get_by_type(PartitionType.TRAIN)) == 1
    assert p1.contains(date(2018, 6, 1))
    assert not p1.contains(date(2022, 1, 1))


def test_partition_scheme_rejects_overlapping_dates() -> None:
    p1 = TimePartition("P1", PartitionType.TRAIN, date(2015, 1, 1), date(2021, 6, 1))
    p2 = TimePartition("P2", PartitionType.VALIDATION, date(2021, 1, 1), date(2023, 12, 31))

    with pytest.raises(ValueError, match="Partition overlap detected"):
        PartitionScheme((p1, p2))
