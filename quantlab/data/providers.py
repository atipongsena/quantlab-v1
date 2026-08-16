from __future__ import annotations

import csv
import io
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

from quantlab.common.errors import QuantLabError
from quantlab.common.hashing import canonical_hash


class ProviderError(QuantLabError):
    """Raised when a data provider encounters an unrecoverable failure."""


class RateLimitExceededError(ProviderError):
    """Raised when provider rate limits are hit."""


@dataclass(frozen=True, slots=True)
class ProviderPayload:
    provider_name: str
    dataset: str
    fetch_params: dict[str, object]
    content: bytes
    content_hash: str
    fetched_at: datetime

    @classmethod
    def create(
        cls,
        provider_name: str,
        dataset: str,
        fetch_params: Mapping[str, object],
        content: bytes,
        fetched_at: datetime | None = None,
    ) -> ProviderPayload:
        now = fetched_at or datetime.now(UTC)
        h = canonical_hash({"content_len": len(content), "params": dict(fetch_params)})
        return cls(
            provider_name=provider_name,
            dataset=dataset,
            fetch_params=dict(fetch_params),
            content=content,
            content_hash=h,
            fetched_at=now,
        )


class DataProvider(Protocol):
    def fetch_eod(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> ProviderPayload: ...

    def fetch_actions(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> ProviderPayload: ...

    def fetch_fundamentals(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> ProviderPayload: ...


def retry_with_backoff[T](
    operation: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 0.01,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple[type[Exception], ...] = (RateLimitExceededError,),
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    """Execute operation with exponential backoff on retryable exceptions."""
    delay = initial_delay
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except retry_exceptions as err:
            last_err = err
            if attempt == max_retries:
                raise
            sleep_fn(delay)
            delay *= backoff_factor
    assert last_err is not None
    raise last_err


class SyntheticFixtureProvider:
    def __init__(
        self,
        fixture_dir: str | None = None,
        rate_limit_failure_count: int = 0,
    ) -> None:
        from pathlib import Path

        self._fixture_dir = Path(fixture_dir or "data/fixtures/synthetic_v1/source")
        self._provider_name = "synthetic_fixture"
        self._failures_remaining = rate_limit_failure_count

    def _check_simulated_rate_limit(self) -> None:
        if self._failures_remaining > 0:
            self._failures_remaining -= 1
            raise RateLimitExceededError("Simulated 429 Too Many Requests rate limit")

    def fetch_eod(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> ProviderPayload:
        self._check_simulated_rate_limit()
        symbols_upper = {s.upper() for s in symbols}
        prices_file = self._fixture_dir / "prices.csv"
        if not prices_file.exists():
            raise ProviderError(f"Missing fixture file: {prices_file}")

        out_rows: list[dict[str, str]] = []
        with open(prices_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                sym = row["symbol"].upper()
                dt = date.fromisoformat(row["date"])
                if (not symbols_upper or sym in symbols_upper) and (start_date <= dt <= end_date):
                    out_rows.append(row)

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
        content = buf.getvalue().encode("utf-8")

        return ProviderPayload.create(
            provider_name=self._provider_name,
            dataset="prices",
            fetch_params={
                "symbols": sorted(symbols_upper),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            content=content,
        )

    def fetch_actions(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> ProviderPayload:
        self._check_simulated_rate_limit()
        symbols_upper = {s.upper() for s in symbols}
        actions_file = self._fixture_dir / "actions.csv"
        if not actions_file.exists():
            raise ProviderError(f"Missing fixture file: {actions_file}")

        out_rows: list[dict[str, str]] = []
        with open(actions_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                sym = row["symbol"].upper()
                dt = date.fromisoformat(row["effective_date"])
                if (not symbols_upper or sym in symbols_upper) and (start_date <= dt <= end_date):
                    out_rows.append(row)

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
        content = buf.getvalue().encode("utf-8")

        return ProviderPayload.create(
            provider_name=self._provider_name,
            dataset="actions",
            fetch_params={
                "symbols": sorted(symbols_upper),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            content=content,
        )

    def fetch_fundamentals(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> ProviderPayload:
        self._check_simulated_rate_limit()
        symbols_upper = {s.upper() for s in symbols}
        funds_file = self._fixture_dir / "fundamentals.csv"
        if not funds_file.exists():
            raise ProviderError(f"Missing fixture file: {funds_file}")

        out_rows: list[dict[str, str]] = []
        with open(funds_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                sym = row["symbol"].upper()
                avail = datetime.fromisoformat(row["available_at"]).date()
                if (not symbols_upper or sym in symbols_upper) and (
                    start_date <= avail <= end_date
                ):
                    out_rows.append(row)

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
        content = buf.getvalue().encode("utf-8")

        return ProviderPayload.create(
            provider_name=self._provider_name,
            dataset="fundamentals",
            fetch_params={
                "symbols": sorted(symbols_upper),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            content=content,
        )
