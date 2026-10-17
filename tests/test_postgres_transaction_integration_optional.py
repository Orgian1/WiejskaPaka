"""Opt-in transaction smoke tests on a disposable PostgreSQL database.

No permanent tables or schema modifications. A temporary table is created
inside the connection and automatically discarded on commit/rollback.
"""
import os
import pytest

from backend.pg_adapter import postgres_db
from backend.postgres_test_guard import require_disposable_postgres


def _test_url():
    url = os.getenv('WP_TEST_DATABASE_URL')
    if not url:
        pytest.skip('WP_TEST_DATABASE_URL not set; PostgreSQL integration not executed')
    require_disposable_postgres(url)
    return url


def test_postgres_adapter_parameter_binding_and_transaction():
    url = _test_url()
    with postgres_db(url) as db:
        db.execute('CREATE TEMP TABLE wp_temp_tx_check (amount_grosze bigint NOT NULL CHECK (amount_grosze >= 0)) ON COMMIT DROP')
        db.execute('INSERT INTO wp_temp_tx_check (amount_grosze) VALUES (?)', (123,))
        assert db.execute('SELECT amount_grosze FROM wp_temp_tx_check').fetchone()['amount_grosze'] == 123
        assert db.execute('SELECT ? AS literal_value', ('test',)).fetchone()['literal_value'] == 'test'
    with postgres_db(url) as db:
        assert db.execute("SELECT to_regclass('pg_temp.wp_temp_tx_check') AS tbl").fetchone()['tbl'] is None


def test_postgres_adapter_rollback_on_error():
    url = _test_url()
    with pytest.raises(RuntimeError, match='rollback sentinel'):
        with postgres_db(url) as db:
            db.execute('CREATE TEMP TABLE wp_temp_rollback_check (id integer)')
            db.execute('INSERT INTO wp_temp_rollback_check (id) VALUES (?)', (1,))
            raise RuntimeError('rollback sentinel')
    with postgres_db(url) as db:
        assert db.execute('SELECT 1 AS healthy').fetchone()['healthy'] == 1
