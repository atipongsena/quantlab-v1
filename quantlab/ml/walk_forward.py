"""Purged, embargoed walk-forward cross-validation splitter."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from quantlab.ml.splits import FoldSplit, WalkForwardSpec, WindowType


class PurgedWalkForwardCV:
    """Generates non-overlapping temporal walk-forward evaluation folds."""

    @classmethod
    def split(
        cls,
        sessions: Sequence[date],
        spec: WalkForwardSpec | None = None,
    ) -> tuple[FoldSplit, ...]:
        wf_spec = spec or WalkForwardSpec()
        sorted_sessions = sorted(sessions)
        n = len(sorted_sessions)

        folds: list[FoldSplit] = []
        min_train = wf_spec.min_train_sessions
        test_win = wf_spec.test_window_sessions
        purge = wf_spec.purge_sessions
        step = wf_spec.step_sessions

        # First possible test start is after min_train + purge
        current_test_start_idx = min_train + purge
        fold_idx = 0

        while current_test_start_idx + test_win <= n:
            test_end_idx = current_test_start_idx + test_win
            test_sessions = tuple(sorted_sessions[current_test_start_idx:test_end_idx])

            # Train end is before purge gap
            train_end_idx = current_test_start_idx - purge
            if wf_spec.window_type == WindowType.EXPANDING:
                train_start_idx = 0
            else:  # ROLLING
                train_start_idx = max(0, train_end_idx - wf_spec.train_window_sessions)

            train_sessions = tuple(sorted_sessions[train_start_idx:train_end_idx])
            if len(train_sessions) >= min_train:
                folds.append(
                    FoldSplit(
                        fold_index=fold_idx,
                        train_sessions=train_sessions,
                        test_sessions=test_sessions,
                        train_start=train_sessions[0],
                        train_end=train_sessions[-1],
                        test_start=test_sessions[0],
                        test_end=test_sessions[-1],
                        purge_sessions=purge,
                        embargo_sessions=wf_spec.embargo_sessions,
                    )
                )
                fold_idx += 1

            current_test_start_idx += step

        return tuple(folds)
