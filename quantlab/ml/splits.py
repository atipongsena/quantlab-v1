"""Temporal cross-validation split contracts and boundary calculators."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class WindowType(StrEnum):
    ROLLING = "rolling"
    EXPANDING = "expanding"


@dataclass(frozen=True, slots=True)
class FoldSplit:
    fold_index: int
    train_sessions: tuple[date, ...]
    test_sessions: tuple[date, ...]
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    purge_sessions: int
    embargo_sessions: int

    def __post_init__(self) -> None:
        if self.train_end >= self.test_start:
            raise ValueError(
                f"Train end {self.train_end} must precede test start {self.test_start}"
            )


@dataclass(frozen=True, slots=True)
class WalkForwardSpec:
    window_type: WindowType = WindowType.EXPANDING
    min_train_sessions: int = 252
    train_window_sessions: int = 504  # Used for rolling window
    test_window_sessions: int = 63  # Quarterly test slice (~3 months)
    step_sessions: int = 63  # Roll step
    purge_sessions: int = 21  # 1-month label horizon purge gap
    embargo_sessions: int = 5  # 5-session post-test embargo
