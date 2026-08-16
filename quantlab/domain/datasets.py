from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from quantlab.domain.identity import _require_nonempty, require_timezone_aware


class DatasetStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    status: DatasetStatus
    created_at: datetime
    as_of: datetime
    source: str
    content_hash: str
    row_count: int

    def __post_init__(self) -> None:
        _require_nonempty(self.dataset_id, "dataset_id")
        if not isinstance(self.status, DatasetStatus):
            raise TypeError("status must be DatasetStatus")
        require_timezone_aware(self.created_at, "created_at")
        require_timezone_aware(self.as_of, "as_of")
        _require_nonempty(self.source, "source")
        _require_nonempty(self.content_hash, "content_hash")
        if not isinstance(self.row_count, int):
            raise TypeError("row_count must be an integer")
        if self.row_count < 0:
            raise ValueError("row_count must be nonnegative")
