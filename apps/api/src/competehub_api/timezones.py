from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

PRODUCT_TIMEZONE_NAME = "Asia/Shanghai"
PRODUCT_TIMEZONE = ZoneInfo(PRODUCT_TIMEZONE_NAME)


def product_date_start_utc(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=PRODUCT_TIMEZONE).astimezone(UTC)


def product_datetime_as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=PRODUCT_TIMEZONE)
    return value.astimezone(UTC)


def stored_datetime_as_utc(value: datetime) -> datetime:
    # SQLite drops offsets on reload; persisted naive values still represent normalized UTC.
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
