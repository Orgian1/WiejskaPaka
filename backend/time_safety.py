"""Normalize timestamp values returned by SQLite (text) and psycopg (datetime)."""
from datetime import datetime, timezone


def utc_datetime(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    else:
        raise ValueError('Unsupported timestamp type')
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Timezone is required for security timestamps')
    return parsed.astimezone(timezone.utc)


def is_future(value, now):
    return utc_datetime(value) > utc_datetime(now)
