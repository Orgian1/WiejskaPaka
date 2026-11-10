from datetime import datetime, timezone, timedelta
import pytest
from backend.time_safety import utc_datetime, is_future

NOW = datetime(2026, 10, 14, 20, 0, tzinfo=timezone.utc)

@pytest.mark.parametrize('value', [
    '2026-10-14T20:01:00+00:00',
    '2026-10-14T22:01:00+02:00',
    '2026-10-14T20:01:00Z',
    NOW + timedelta(minutes=1),
])
def test_future_lockout(value):
    assert is_future(value, NOW)

@pytest.mark.parametrize('value', [
    '2026-10-14T20:00:00+00:00',
    '2026-10-14T21:59:00+02:00',
    NOW - timedelta(seconds=1),
])
def test_expired_lockout(value):
    assert not is_future(value, NOW)

@pytest.mark.parametrize('value', ['2026-10-14T20:01:00', datetime(2026, 10, 14, 20, 1), None])
def test_reject_naive_or_invalid(value):
    with pytest.raises(ValueError):
        utc_datetime(value)
