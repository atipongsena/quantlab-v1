"""Exchange trading calendar and session schedule."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, tzinfo


class EasternTimeZone(tzinfo):
    """Offline-safe US Eastern Time implementation (EST/EDT) with DST rules."""

    def _is_dst(self, dt: datetime) -> bool:
        # Determine 2nd Sunday in March and 1st Sunday in Nov for dt.year
        year = dt.year
        # 2nd Sunday in March: day in [8..14]
        mar8 = date(year, 3, 8)
        dst_start_day = 8 + (6 - mar8.weekday()) % 7
        dst_start = datetime(year, 3, dst_start_day, 2, 0)

        # 1st Sunday in Nov: day in [1..7]
        nov1 = date(year, 11, 1)
        dst_end_day = 1 + (6 - nov1.weekday()) % 7
        dst_end = datetime(year, 11, dst_end_day, 2, 0)

        # Compare naive or local time
        naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
        return dst_start <= naive < dst_end

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        if dt is None:
            return timedelta(hours=-5)
        return timedelta(hours=-4) if self._is_dst(dt) else timedelta(hours=-5)

    def dst(self, dt: datetime | None) -> timedelta | None:
        if dt is None:
            return timedelta(0)
        return timedelta(hours=1) if self._is_dst(dt) else timedelta(0)

    def tzname(self, dt: datetime | None) -> str | None:
        if dt is None:
            return "EST"
        return "EDT" if self._is_dst(dt) else "EST"


NYC_TZ = EasternTimeZone()


class TradingCalendar:
    """NYSE / US Equity Trading Calendar with standard holiday closures."""

    # Fixed holidays and rule-based holidays
    @classmethod
    def is_weekend(cls, session: date) -> bool:
        return session.weekday() >= 5

    @classmethod
    def is_holiday(cls, session: date) -> bool:
        year = session.year
        month = session.month
        day = session.day
        weekday = session.weekday()  # 0: Mon, ..., 6: Sun

        # New Year's Day (Jan 1, observed Mon if Sun, Fri if Sat)
        if month == 1 and day == 1:
            return True
        if month == 1 and day == 2 and weekday == 0:
            return True
        if month == 12 and day == 31 and weekday == 4:
            return True

        # MLK Day: 3rd Monday in January
        if month == 1 and weekday == 0 and 15 <= day <= 21:
            return True

        # Washington's Birthday (Presidents' Day): 3rd Monday in February
        if month == 2 and weekday == 0 and 15 <= day <= 21:
            return True

        # Memorial Day: Last Monday in May
        if month == 5 and weekday == 0 and day >= 25:
            return True

        # Juneteenth National Independence Day (June 19, observed)
        if year >= 2021:
            if month == 6 and day == 19:
                return True
            if month == 6 and day == 20 and weekday == 0:
                return True
            if month == 6 and day == 18 and weekday == 4:
                return True

        # Independence Day (July 4, observed)
        if month == 7 and day == 4:
            return True
        if month == 7 and day == 5 and weekday == 0:
            return True
        if month == 7 and day == 3 and weekday == 4:
            return True

        # Labor Day: 1st Monday in September
        if month == 9 and weekday == 0 and day <= 7:
            return True

        # Thanksgiving Day: 4th Thursday in November
        if month == 11 and weekday == 3 and 22 <= day <= 28:
            return True

        # Christmas Day (Dec 25, observed)
        if month == 12 and day == 25:
            return True
        if month == 12 and day == 26 and weekday == 0:
            return True
        if month == 12 and day == 24 and weekday == 4:
            return True

        return False

    @classmethod
    def is_session(cls, session: date) -> bool:
        """Check if date is an active trading session."""
        if cls.is_weekend(session):
            return False
        if cls.is_holiday(session):
            return False
        return True

    @classmethod
    def get_sessions(cls, start: date, end: date) -> tuple[date, ...]:
        """Get all trading sessions in the inclusive date range [start, end]."""
        sessions: list[date] = []
        cur = start
        while cur <= end:
            if cls.is_session(cur):
                sessions.append(cur)
            cur += timedelta(days=1)
        return tuple(sessions)

    @classmethod
    def next_session(cls, session: date) -> date:
        """Return the next trading session strictly after the given date."""
        cur = session + timedelta(days=1)
        while not cls.is_session(cur):
            cur += timedelta(days=1)
        return cur

    @classmethod
    def session_open_utc(cls, session: date) -> datetime:
        """Standard market open (09:30 Eastern) converted to UTC datetime."""
        dt_ny = datetime.combine(session, time(9, 30), tzinfo=NYC_TZ)
        return dt_ny.astimezone(UTC)

    @classmethod
    def session_close_utc(cls, session: date) -> datetime:
        """Standard market close (16:00 Eastern) converted to UTC datetime."""
        dt_ny = datetime.combine(session, time(16, 0), tzinfo=NYC_TZ)
        return dt_ny.astimezone(UTC)
