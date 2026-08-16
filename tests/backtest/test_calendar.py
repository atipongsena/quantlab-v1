"""Tests for NYSE TradingCalendar."""

from datetime import date

from quantlab.backtest.calendar import TradingCalendar


def test_trading_calendar_weekends_and_holidays() -> None:
    # 2026-01-01 is Thursday (New Year's Day)
    assert not TradingCalendar.is_session(date(2026, 1, 1))

    # 2026-01-02 is Friday (normal trading day)
    assert TradingCalendar.is_session(date(2026, 1, 2))

    # 2026-01-03 is Saturday
    assert not TradingCalendar.is_session(date(2026, 1, 3))

    # 2026-01-04 is Sunday
    assert not TradingCalendar.is_session(date(2026, 1, 4))

    # 2026-01-19 is 3rd Monday in Jan (MLK Day)
    assert not TradingCalendar.is_session(date(2026, 1, 19))


def test_trading_calendar_sessions_range_and_next() -> None:
    sessions = TradingCalendar.get_sessions(date(2026, 1, 1), date(2026, 1, 7))
    # 1/1 (Thu, holiday), 1/2 (Fri, open), 1/3-1/4 (weekend),
    # 1/5 (Mon, open), 1/6 (Tue, open), 1/7 (Wed, open)
    expected = (date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7))
    assert sessions == expected

    # next_session from Friday 1/2 is Monday 1/5
    assert TradingCalendar.next_session(date(2026, 1, 2)) == date(2026, 1, 5)


def test_trading_calendar_utc_open_close() -> None:
    session = date(2026, 1, 2)
    open_utc = TradingCalendar.session_open_utc(session)
    close_utc = TradingCalendar.session_close_utc(session)

    # In winter (EST = UTC-5): 09:30 EST = 14:30 UTC, 16:00 EST = 21:00 UTC
    assert open_utc.hour == 14
    assert open_utc.minute == 30
    assert close_utc.hour == 21
    assert close_utc.minute == 0
