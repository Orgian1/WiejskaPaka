"""Reset protocol on synthetic SQLite, with deterministic expiry and budgets."""
from datetime import datetime, timedelta, timezone
import sqlite3

from argon2 import PasswordHasher
import pytest

from backend import password_reset as reset

NOW = datetime(2026, 10, 17, tzinfo=timezone.utc)
OLD, NEW = 'Old-synthetic-password!', 'New-synthetic-password!'


@pytest.fixture
def store():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT,password_hash TEXT);
        CREATE TABLE sessions(token_hash TEXT,user_id INTEGER,expires_at TEXT);
        CREATE TABLE login_attempts(email TEXT PRIMARY KEY,failures INTEGER,locked_until TEXT);''')
    con.executescript(reset.SCHEMA_SQLITE)
    hasher = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    con.execute('INSERT INTO users VALUES(1,?,?)', ('test@example.invalid',hasher.hash(OLD)))
    con.execute("INSERT INTO sessions VALUES('first',1,'later')")
    con.execute("INSERT INTO sessions VALUES('other-account',2,'later')")
    con.commit()
    yield con, hasher
    con.close()


def test_single_use_and_revocation_leave_other_accounts_untouched(store):
    con, hasher = store
    first = reset.issue(con, ' TEST@example.invalid ', now=NOW)
    second = reset.issue(con, 'test@example.invalid', now=NOW)
    rows = con.execute('SELECT * FROM password_reset_tokens').fetchall()
    assert len(rows) == 2 and all(first not in str(tuple(r)) and second not in str(tuple(r)) for r in rows)
    assert reset.consume(con, hasher, first, NEW, now=NOW) == 200
    assert hasher.verify(con.execute('SELECT password_hash FROM users').fetchone()[0], NEW)
    assert con.execute('SELECT token_hash FROM sessions').fetchall()[0][0] == 'other-account'
    assert con.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 1
    assert reset.consume(con, hasher, first, NEW, now=NOW) == 400
    assert reset.consume(con, hasher, second, NEW, now=NOW) == 400


@pytest.mark.parametrize('delta', [-1, 900, 901])
def test_future_or_expired_token_is_rejected_without_password_or_session_change(store, delta):
    con, hasher = store
    token = reset.issue(con, 'test@example.invalid', now=NOW)
    assert reset.consume(con, hasher, token, NEW, now=NOW+timedelta(seconds=delta)) == 400
    assert hasher.verify(con.execute('SELECT password_hash FROM users').fetchone()[0], OLD)
    assert con.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 2


def test_password_change_invalidates_previous_link(store):
    con, hasher = store
    token = reset.issue(con, 'test@example.invalid', now=NOW)
    con.execute('UPDATE users SET password_hash=?', (hasher.hash(NEW),))
    assert reset.consume(con, hasher, token, 'Another-new-password!', now=NOW) == 400


def test_unknown_email_has_random_unbound_token_and_identical_request_budget(store):
    con, hasher = store
    for email in ('test@example.invalid', 'missing@example.invalid'):
        tokens = [reset.issue(con, email, now=NOW) for _ in range(3)]
        assert len(set(tokens)) == 3 and all(len(t) == 43 for t in tokens)
        assert reset.issue(con, email.upper(), now=NOW) is None
    assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0] == 3
    assert reset.consume(con, hasher, tokens[0], NEW, now=NOW) == 400
    assert reset.issue(con, 'test@example.invalid', now=NOW+timedelta(minutes=15))
    assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0] == 1


def test_global_request_cap_bounds_unknown_email_bucket_rows(store):
    con, _ = store
    for i in range(100):
        assert reset.issue(con, f'{i}@example.invalid', now=NOW)
    assert reset.issue(con, 'another@example.invalid', now=NOW) is None
    assert con.execute('SELECT COUNT(*) FROM password_reset_limits').fetchone()[0] == 101
    assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0] == 0


def test_invalid_confirmations_are_persistently_rate_limited(store):
    con, hasher = store
    for _ in range(100):
        assert reset.consume(con, hasher, 'wrong', NEW, now=NOW) == 400
    assert reset.consume(con, hasher, 'wrong', NEW, now=NOW) == 429
    assert reset.consume(con, hasher, 'wrong', NEW, now=NOW+timedelta(minutes=15)) == 400


def test_outbox_is_private_and_never_uses_email_as_filename(tmp_path):
    import json, os
    box = tmp_path/'mail'
    message = reset.deliver_demo(box, '../synthetic@example.invalid', 'secret')
    assert message.parent == box and '../' not in message.name
    assert json.loads(message.read_text())['fragment'] == '#reset-token=secret'
    if os.name == 'posix':
        assert message.stat().st_mode & 0o077 == 0
        assert box.stat().st_mode & 0o077 == 0


def test_outbox_rejects_symlink_and_public_directory(tmp_path):
    import os
    if os.name != 'posix':
        pytest.skip('POSIX permissions and symlinks')
    box = tmp_path/'mail'
    box.mkdir(mode=0o755)
    with pytest.raises(ValueError):
        reset.prepare_outbox(box)
    link = tmp_path/'link'
    link.symlink_to(box, target_is_directory=True)
    with pytest.raises(ValueError):
        reset.prepare_outbox(link)


def test_failure_after_password_update_rolls_back_entire_reset(store):
    con, hasher = store
    token = reset.issue(con, 'test@example.invalid', now=NOW)
    con.commit()
    con.execute("CREATE TRIGGER fail_revoke BEFORE DELETE ON sessions BEGIN SELECT RAISE(ABORT,'fault'); END")
    con.commit()
    with pytest.raises(sqlite3.IntegrityError), con:
        reset.consume(con, hasher, token, NEW, now=NOW)
    assert hasher.verify(con.execute('SELECT password_hash FROM users').fetchone()[0], OLD)
    assert con.execute('SELECT COUNT(*) FROM password_reset_tokens').fetchone()[0] == 1
    assert con.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 2
