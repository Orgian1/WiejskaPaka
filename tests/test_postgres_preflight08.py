import sqlite3
from database.postgres_preflight import compare, source_structure


def test_reports_missing_nonempty_table():
    report = compare({'orders': {'rows': 2, 'columns': ['id']}}, {})
    assert not report['structural_preflight_passed']
    assert report['differences'][0]['problem'] == 'missing_table'


def test_reports_missing_nonempty_column():
    report = compare({'orders': {'rows': 1, 'columns': ['id', 'pin_hash']}}, {'orders': {'id'}})
    assert not report['structural_preflight_passed']
    assert report['differences'][0]['columns'] == ['pin_hash']


def test_empty_table_warning_not_blocking():
    report = compare({'orders': {'rows': 0, 'columns': ['id']}}, {})
    assert report['structural_preflight_passed']
    assert not report['safe_for_automatic_migration']


def test_source_read_only_and_columns(tmp_path):
    db = tmp_path / 'example.db'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE example (id INTEGER PRIMARY KEY, value TEXT)')
        con.execute("INSERT INTO example(value) VALUES ('ok')")
    data = source_structure(db)
    assert data['example'] == {'rows': 1, 'columns': ['id', 'value']}
    assert source_structure(db) == data


def test_nonexistent_sqlite_does_not_create_file(tmp_path):
    db = tmp_path / 'missing.db'
    try:
        source_structure(db)
    except ValueError:
        pass
    else:
        assert False, 'Expected ValueError'
    assert not db.exists()
