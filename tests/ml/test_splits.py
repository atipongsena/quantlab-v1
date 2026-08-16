"""Tests for temporal split contracts."""

from datetime import date

import pytest

from quantlab.ml.splits import FoldSplit


def test_fold_split_enforces_temporal_precedence() -> None:
    train_start = date(2020, 1, 1)
    train_end = date(2020, 12, 31)
    test_start = date(2021, 2, 1)  # 1 month purge gap
    test_end = date(2021, 3, 31)

    split = FoldSplit(
        fold_index=0,
        train_sessions=(train_start, train_end),
        test_sessions=(test_start, test_end),
        train_start=train_start,
        train_end=train_end,
        test_start=test_start,
        test_end=test_end,
        purge_sessions=21,
        embargo_sessions=5,
    )
    assert split.fold_index == 0
    assert split.train_end < split.test_start


def test_fold_split_rejects_overlapping_train_test() -> None:
    d1 = date(2020, 1, 1)
    d2 = date(2020, 6, 1)

    with pytest.raises(ValueError, match="Train end.*must precede test start"):
        FoldSplit(
            fold_index=0,
            train_sessions=(d1, d2),
            test_sessions=(d1, d2),
            train_start=d1,
            train_end=d2,
            test_start=d1,
            test_end=d2,
            purge_sessions=0,
            embargo_sessions=0,
        )
