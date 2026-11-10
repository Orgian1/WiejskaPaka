"""Optional real-PostgreSQL integration probes; no production database allowed."""
import os
import pytest


def test_postgres_server_version_and_transaction():
    dsn = os.getenv('WP_TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('WP_TEST_POSTGRES_DSN not configured')
    from backend.postgres_test_guard import require_disposable_postgres
    require_disposable_postgres(dsn)
    psycopg = pytest.importorskip('psycopg')
    with psycopg.connect(dsn) as con:
        version = con.execute('SHOW server_version_num').fetchone()[0]
        assert int(version) >= 140000
        with pytest.raises(RuntimeError):
            with con.transaction():
                con.execute('CREATE TEMP TABLE wp_integration_rollback (v integer)')
                con.execute('INSERT INTO wp_integration_rollback VALUES (123)')
                raise RuntimeError('force rollback')
        assert con.execute('SELECT 42').fetchone()[0] == 42


def test_postgres_schema_on_isolated_rolled_back_transaction():
    dsn = os.getenv('WP_TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('WP_TEST_POSTGRES_DSN not configured')
    from backend.postgres_test_guard import require_disposable_postgres
    require_disposable_postgres(dsn)
    psycopg = pytest.importorskip('psycopg')
    from pathlib import Path
    schema = (Path(__file__).resolve().parents[1] / 'database/postgres_schema.sql').read_text()
    # Schema SQL contains BEGIN/COMMIT, so use a disposable isolated schema and
    # rollback the outer transaction using connection autocommit=False.
    # Instead create the schema in a dedicated temporary DB namespace and drop it.
    import uuid
    namespace = 'wp_test_' + uuid.uuid4().hex[:12]
    with psycopg.connect(dsn) as con:
        with con.cursor() as cur:
            cur.execute('CREATE SCHEMA "' + namespace + '"')
            cur.execute('SET search_path TO "' + namespace + '"')
            try:
                cur.execute(schema)
                cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = %s", (namespace,))
                assert cur.fetchone()[0] >= 8
            finally:
                cur.execute('RESET search_path')
                cur.execute('DROP SCHEMA IF EXISTS "' + namespace + '" CASCADE')
