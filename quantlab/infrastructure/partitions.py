from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from quantlab.common.errors import QuantLabError
from quantlab.common.hashing import canonical_hash

# Partitions are newline-free JSON documents, not Parquet. The previous name and
# extension advertised a columnar format the code never wrote, which is the kind of
# detail a reader takes on trust and should not have to.
PARTITION_SUFFIX = ".json"


class PartitionStorageError(QuantLabError):
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
    partition_file = partition_dir / f"{partition_key}{PARTITION_SUFFIX}"

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


_PARTITION_CACHE_LIMIT = 4096
_partition_cache: OrderedDict[tuple[str, int, int], tuple[dict[str, object], ...]] = OrderedDict()


def clear_partition_cache() -> None:
    """Drop every cached partition. Tests that rewrite files in place call this."""
    _partition_cache.clear()


def _cache_key(path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return (str(path), stat.st_size, stat.st_mtime_ns)


def read_partition(ref: PartitionRef) -> list[dict[str, object]]:
    path = Path(ref.uri)
    if not path.is_file():
        raise PartitionStorageError(f"Partition file not found: {path}")

    # A research run walks the same instrument-year partitions once per rebalance, so a
    # thirty-year study re-parses each file hundreds of times. The cache is keyed on size
    # and mtime, so a rewritten partition invalidates itself rather than going stale.
    key = _cache_key(path)
    cached = _partition_cache.get(key)
    if cached is not None:
        _partition_cache.move_to_end(key)
        return [dict(row) for row in cached]

    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise PartitionStorageError(f"Corrupt partition file at {path}: {err}") from err

    data = content.get("data")
    if not isinstance(data, list):
        raise PartitionStorageError(f"Invalid partition payload in {path}")

    rows = tuple(dict(row) for row in data)
    _partition_cache[key] = rows
    _partition_cache.move_to_end(key)
    while len(_partition_cache) > _PARTITION_CACHE_LIMIT:
        _partition_cache.popitem(last=False)

    return [dict(row) for row in rows]
