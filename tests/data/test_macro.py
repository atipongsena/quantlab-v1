from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from migrations.env import run_migrations
from quantlab.data.macro import MacroVintage, SqlMacroStore
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine


def test_macro_vintage_validation() -> None:
    v = MacroVintage(
        series_id="GDP",
        period_date=date(2020, 1, 1),
        release_time=datetime(2020, 4, 30, 12, 30, tzinfo=UTC),
        value=Decimal("21560.5"),
        source="BEA",
    )
    assert v.series_id == "GDP"

    with pytest.raises(TypeError, match="must be Decimal"):
        MacroVintage(
            series_id="GDP",
            period_date=date(2020, 1, 1),
            release_time=datetime(2020, 4, 30, 12, 30, tzinfo=UTC),
            value=21560.5,  # type: ignore[arg-type]
            source="BEA",
        )


def test_sql_macro_store_pit_lag_invariance() -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
    applied = run_migrations(engine)
    assert "0004_macro" in applied
    store = SqlMacroStore(engine)

    # Q1 2020 GDP - Advance estimate released 2020-04-30
    advance_gdp = MacroVintage(
        series_id="GDP",
        period_date=date(2020, 1, 1),
        release_time=datetime(2020, 4, 30, 12, 30, tzinfo=UTC),
        value=Decimal("21537.9"),
        source="BEA:Advance",
    )
    # Q1 2020 GDP - Second estimate released 2020-05-28
    second_gdp = MacroVintage(
        series_id="GDP",
        period_date=date(2020, 1, 1),
        release_time=datetime(2020, 5, 28, 12, 30, tzinfo=UTC),
        value=Decimal("21561.2"),
        source="BEA:Second",
    )
    # Q1 2020 GDP - Third estimate released 2020-06-25
    third_gdp = MacroVintage(
        series_id="GDP",
        period_date=date(2020, 1, 1),
        release_time=datetime(2020, 6, 25, 12, 30, tzinfo=UTC),
        value=Decimal("21560.5"),
        source="BEA:Third",
    )

    store.record_vintages([advance_gdp, second_gdp, third_gdp])

    # 1. Query before advance release (2020-04-01) -> None
    assert store.as_of("GDP", datetime(2020, 4, 1, 0, 0, tzinfo=UTC), date(2020, 1, 1)) is None

    # 2. Query after advance release (2020-05-01) -> Advance estimate (21537.9)
    res_may1 = store.as_of("GDP", datetime(2020, 5, 1, 0, 0, tzinfo=UTC), date(2020, 1, 1))
    assert res_may1 is not None
    assert res_may1.value == Decimal("21537.9")

    # 3. Query after second release (2020-06-01) -> Second estimate (21561.2)
    res_jun1 = store.as_of("GDP", datetime(2020, 6, 1, 0, 0, tzinfo=UTC), date(2020, 1, 1))
    assert res_jun1 is not None
    assert res_jun1.value == Decimal("21561.2")

    # 4. Query after third release (2020-07-01) -> Third estimate (21560.5)
    res_jul1 = store.as_of("GDP", datetime(2020, 7, 1, 0, 0, tzinfo=UTC), date(2020, 1, 1))
    assert res_jul1 is not None
    assert res_jul1.value == Decimal("21560.5")

    # 5. Full history for period
    vintages = store.vintages_for_period("GDP", date(2020, 1, 1))
    assert len(vintages) == 3
    assert vintages[0].value == Decimal("21537.9")
    assert vintages[1].value == Decimal("21561.2")
    assert vintages[2].value == Decimal("21560.5")
