"""Tests for PurgedWalkForwardCV splitter."""

from datetime import date

from quantlab.ml.splits import WalkForwardSpec, WindowType
from quantlab.ml.walk_forward import PurgedWalkForwardCV


def test_purged_walk_forward_cv_generation() -> None:
    # 500 trading sessions
    sessions = [date(2020, 1, 1).fromordinal(date(2020, 1, 1).toordinal() + i) for i in range(500)]

    spec = WalkForwardSpec(
        window_type=WindowType.EXPANDING,
        min_train_sessions=200,
        test_window_sessions=50,
        step_sessions=50,
        purge_sessions=20,
        embargo_sessions=5,
    )

    folds = PurgedWalkForwardCV.split(sessions, spec)
    assert len(folds) >= 4

    for fold in folds:
        # Distance between train_end and test_start must be >= purge_sessions
        train_end_idx = sessions.index(fold.train_end)
        test_start_idx = sessions.index(fold.test_start)
        assert test_start_idx - train_end_idx >= spec.purge_sessions
