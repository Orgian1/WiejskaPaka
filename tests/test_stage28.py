import pytest
from tests.test_stage25 import ready
from backend.payout_scheduler import SCHEMA_SQLITE, prepare_weekly_run


def test_weekly_run_and_replay():
    con = ready()
    con.executescript(SCHEMA_SQLITE)
    con.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'rolnik'")
    first = prepare_weekly_run(con, '2026-10-19', 'now')
    assert first['farmer_count'] >= 1
    assert first['plan_count'] == 2
    assert first['transfer_executed'] is False
    again = prepare_weekly_run(con, '2026-10-19', 'later')
    assert again['already_prepared'] is True
    assert con.execute('SELECT COUNT(*) FROM payout_schedule_runs').fetchone()[0] == 1
    assert con.execute('SELECT COUNT(*) FROM payout_plan_items').fetchone()[0] == 2


def test_only_mondays():
    con = ready()
    con.executescript(SCHEMA_SQLITE)
    con.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'rolnik'")
    with pytest.raises(ValueError):
        prepare_weekly_run(con, '2026-10-20', 'now')
    assert con.execute('SELECT COUNT(*) FROM payout_schedule_runs').fetchone()[0] == 0
