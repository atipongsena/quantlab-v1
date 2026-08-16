from __future__ import annotations

from datetime import date

import pytest

from quantlab.data.providers import (
    RateLimitExceededError,
    SyntheticFixtureProvider,
    retry_with_backoff,
)


def test_synthetic_fixture_provider_fetch_eod_and_filtering() -> None:
    provider = SyntheticFixtureProvider(fixture_dir="data/fixtures/synthetic_v1/source")

    # Fetch AAPL in date range
    payload = provider.fetch_eod(
        symbols=["AAPL"],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 31),
    )
    assert payload.provider_name == "synthetic_fixture"
    assert payload.dataset == "prices"
    assert len(payload.content) > 0

    content_str = payload.content.decode("utf-8")
    assert "AAPL" in content_str
    # MSFT should not be in filtered content
    assert "MSFT" not in content_str


def test_synthetic_fixture_provider_actions_and_fundamentals() -> None:
    provider = SyntheticFixtureProvider(fixture_dir="data/fixtures/synthetic_v1/source")

    actions_payload = provider.fetch_actions(
        symbols=["AAPL"],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 12, 31),
    )
    assert actions_payload.dataset == "actions"
    actions_str = actions_payload.content.decode("utf-8")
    assert "AAPL" in actions_str

    funds_payload = provider.fetch_fundamentals(
        symbols=["AAPL"],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 12, 31),
    )
    assert funds_payload.dataset == "fundamentals"
    funds_str = funds_payload.content.decode("utf-8")
    assert "AAPL" in funds_str


def test_retry_with_backoff_succeeds_after_retries() -> None:
    calls = 0

    def faulty_call() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RateLimitExceededError("Rate limit hit")
        return "success"

    sleep_records: list[float] = []
    res = retry_with_backoff(
        faulty_call,
        max_retries=3,
        initial_delay=0.01,
        backoff_factor=2.0,
        sleep_fn=sleep_records.append,
    )
    assert res == "success"
    assert calls == 3
    assert len(sleep_records) == 2
    assert sleep_records == [0.01, 0.02]


def test_retry_with_backoff_exhausts_retries() -> None:
    calls = 0

    def always_fails() -> str:
        nonlocal calls
        calls += 1
        raise RateLimitExceededError("Persistent rate limit")

    sleep_records: list[float] = []
    with pytest.raises(RateLimitExceededError, match="Persistent rate limit"):
        retry_with_backoff(
            always_fails,
            max_retries=2,
            initial_delay=0.01,
            sleep_fn=sleep_records.append,
        )
    assert calls == 3
    assert len(sleep_records) == 2
