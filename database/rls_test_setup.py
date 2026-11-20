"""Provision the reviewed RLS gateway for a fresh disposable test database."""
from pathlib import Path

from psycopg import sql


def provision(connection, key, login):
    info = connection.info
    if info.host not in ('127.0.0.1', '::1', 'localhost') or not info.dbname.startswith('wp_test_'):
        raise ValueError('A disposable loopback test database is required')
    connection.execute("SET wp_rls.disposable_test='yes'")
    migration = Path(__file__).with_name('security_rls') / '001_gateway.up.sql'
    connection.execute(migration.read_text(encoding='utf-8'))
    connection.execute('INSERT INTO wp_rls_keys.secrets VALUES(true,%s)', (key,))
    role = sql.Identifier(login)
    connection.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}').format(role))
    connection.execute(sql.SQL('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {}').format(role))
    connection.execute(sql.SQL('ALTER ROLE {} INHERIT').format(role))
    connection.execute(sql.SQL('GRANT wp_rls_runtime TO {}').format(role))
