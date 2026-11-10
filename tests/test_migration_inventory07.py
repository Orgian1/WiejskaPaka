import sqlite3
from database.migration_inventory import declared_tables, inventory


def test_inventory_reports_unmapped_nonempty_table(tmp_path):
    db = tmp_path / 'local.db'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE unknown_orders (id INTEGER PRIMARY KEY)')
        con.execute('INSERT INTO unknown_orders VALUES (1)')
    sql = tmp_path / 'sql'
    sql.mkdir()
    (sql / 'schema.sql').write_text('CREATE TABLE users (id BIGINT);')
    report = inventory(db, sql)
    assert report['nonempty_tables_missing_pg_declaration'] == ['unknown_orders']
    assert report['safe_to_run_legacy_migrator'] is False


def test_inventory_is_read_only(tmp_path):
    db = tmp_path / 'local.db'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE users (id INTEGER)')
        con.execute('INSERT INTO users VALUES (1)')
    sql = tmp_path / 'sql'
    sql.mkdir()
    (sql / 'schema.sql').write_text('CREATE TABLE IF NOT EXISTS users (id BIGINT);')
    before = db.read_bytes()
    report = inventory(db, sql)
    assert report['tables'][0]['rows'] == 1
    assert not report['nonempty_tables_missing_pg_declaration']
    assert db.read_bytes() == before


def test_inventory_missing_database_does_not_create_file(tmp_path):
    db = tmp_path / 'missing.db'
    try:
        inventory(db, tmp_path)
    except ValueError:
        pass
    else:
        raise AssertionError('Expected ValueError')
    assert not db.exists()


def test_parser_reads_all_sql_migrations(tmp_path):
    (tmp_path / 'one.sql').write_text('CREATE TABLE "public"."orders" (id BIGINT);')
    (tmp_path / 'two.sql').write_text('CREATE TABLE IF NOT EXISTS payout_batches (id BIGINT);')
    assert declared_tables(tmp_path) == {'orders', 'payout_batches'}
