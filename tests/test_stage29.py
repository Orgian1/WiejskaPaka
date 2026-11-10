from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from backend.weekly_job import execute
from backend.payout_scheduler import SCHEMA_SQLITE
from tests.test_stage25 import ready

TZ = ZoneInfo('Europe/Warsaw')

def setup():
    con = ready()
    con.executescript(SCHEMA_SQLITE)
    con.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'rolnik'")
    return con

def test_weekly_job_idempotent(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    con = setup()
    # ready() uses an in-memory connection; BEGIN IMMEDIATE needs a clean transaction.
    con.commit()
    now = datetime(2026, 10, 19, 9, tzinfo=TZ)
    first = execute(con, now=now, enabled=True)
    assert first['status'] == 'prepared'
    con.commit()
    second = execute(con, now=now, enabled=True)
    assert second['status'] == 'already_prepared'
    assert con.execute('SELECT COUNT(*) FROM payout_schedule_runs').fetchone()[0] == 1

def test_not_monday_does_not_change_data(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    con = setup()
    result = execute(con, now=datetime(2026, 10, 20, 9, tzinfo=TZ), enabled=True)
    assert result['status'] == 'skipped_not_monday'
    assert con.execute('SELECT COUNT(*) FROM payout_schedule_runs').fetchone()[0] == 0

def test_explicit_opt_in_required():
    con = setup()
    with pytest.raises(PermissionError):
        execute(con, now=datetime(2026, 10, 19, tzinfo=TZ))

def test_naive_datetime_rejected():
    con = setup()
    with pytest.raises(ValueError):
        execute(con, now=datetime(2026, 10, 19), enabled=True)
