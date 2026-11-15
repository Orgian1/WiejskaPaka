"""Provision only a freshly-created disposable test DB; never called by startup."""
from pathlib import Path
from psycopg import sql


def provision(connection, key, login):
    row=connection.execute('SELECT current_database()').fetchone()
    name=row[0] if not isinstance(row,dict) else row['current_database']
    if not name.startswith('wp_test_'):raise ValueError('Fresh disposable test database required')
    connection.execute("SET wp_rls.disposable_test='yes'")
    connection.execute((Path(__file__).parent/'security_rls/001_gateway.up.sql').read_text())
    connection.execute('INSERT INTO wp_rls_keys.secrets VALUES(true,%s)',(key,))
    connection.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}').format(sql.Identifier(login)))
    connection.execute(sql.SQL('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {}').format(sql.Identifier(login)))
    connection.execute(sql.SQL('ALTER ROLE {} INHERIT').format(sql.Identifier(login)))
    connection.execute(sql.SQL('GRANT wp_rls_runtime TO {} WITH INHERIT TRUE').format(sql.Identifier(login)))
