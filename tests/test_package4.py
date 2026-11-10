from backend.schema_audit import audit_schema, defined_tables
from backend.pg_adapter import translate_sql


def test_schema_audit_is_deterministic():
    assert audit_schema() == audit_schema()
    assert {'users', 'orders', 'products', 'payment_simulations'} <= set(audit_schema()['sqlite_tables'])


def test_pg_schema_has_core_tables():
    report = audit_schema()
    assert {'users', 'orders', 'products', 'sessions'} <= set(report['postgres_tables'])


def test_schema_parser(tmp_path):
    sql = tmp_path / 'schema.sql'
    sql.write_text('CREATE TABLE IF NOT EXISTS public.orders (id bigint); CREATE TABLE users(id int);')
    assert defined_tables([sql]) == {'orders', 'users'}


def test_sql_placeholders_with_quoted_questions():
    assert translate_sql("SELECT '?' AS q, 'a''?b' AS t WHERE id=?") == "SELECT '?' AS q, 'a''?b' AS t WHERE id=%s"
