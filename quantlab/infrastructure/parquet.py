from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from quantlab.common.errors import QuantLabError
from quantlab.common.hashing import canonical_hash


class ParquetStorageError(QuantLabError):
    """Raised when analytical partition operations fail."""


@dataclass(frozen=True, slots=True)
class PartitionRef:
    dataset_id: str
    table_name: str
    partition_key: str
    uri: str
    row_count: int
    content_hash: str


def write_partition(
    base_dir: Path,
    dataset_id: str,
    table_name: str,
    partition_key: str,
    rows: Sequence[Mapping[str, object]],
    schema: Mapping[str, str] | None = None,
) -> PartitionRef:
    if not dataset_id or not table_name:
        raise ValueError("dataset_id and table_name must be nonempty")

    partition_dir = base_dir / dataset_id / table_name
    partition_dir.mkdir(parents=True, exist_ok=True)
    partition_file = partition_dir / f"{partition_key}.parquet"

    normalized_rows = [dict(row) for row in rows]
    content_hash = canonical_hash(
        {
            "dataset_id": dataset_id,
            "table_name": table_name,
            "partition_key": partition_key,
            "schema": dict(sorted(schema.items())) if schema else {},
            "rows": normalized_rows,
        }
    )

    payload = {
        "dataset_id": dataset_id,
        "table_name": table_name,
        "partition_key": partition_key,
        "schema": dict(schema) if schema else {},
        "row_count": len(normalized_rows),
        "content_hash": content_hash,
        "data": normalized_rows,
    }

    partition_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return PartitionRef(
        dataset_id=dataset_id,
        table_name=table_name,
        partition_key=partition_key,
        uri=partition_file.as_posix(),
        row_count=len(normalized_rows),
        content_hash=content_hash,
    )


def read_partition(ref: PartitionRef) -> list[dict[str, object]]:
    path = Path(ref.uri)
    if not path.is_file():
        raise ParquetStorageError(f"Partition file not found: {path}")

    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise ParquetStorageError(f"Corrupt partition file at {path}: {err}") from err

    data = content.get("data")
    if not isinstance(data, list):
        raise ParquetStorageError(f"Invalid partition payload in {path}")

    return [dict(row) for row in data]
