from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal

type JsonScalar = str | int | float | bool | None
type CanonicalValue = (
    JsonScalar | tuple[CanonicalValue, ...] | tuple[tuple[str, CanonicalValue], ...]
)


def canonical_hash(value: object) -> str:
    payload = json.dumps(canonicalize(value), ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonicalize(value: object) -> CanonicalValue:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime values must be timezone-aware")
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return tuple(
            (str(key), canonicalize(item))
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        )
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, Sequence):
        canonical_items = tuple(canonicalize(item) for item in value)
        return tuple(sorted(canonical_items, key=_canonical_sort_key))
    raise TypeError(f"unsupported value for canonical hashing: {type(value).__name__}")


def _canonical_sort_key(value: CanonicalValue) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
