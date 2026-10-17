import sqlite3
import tempfile
from pathlib import Path
from database.migration_plan import build_plan


def make_db():
    temp = tempfile.TemporaryDirectory()
    path = Path(temp.name) / 'source.sqlite'
    con = sqlite3.connect(path)
    con.executescript('''PRAGMA foreign_keys=ON;
        CREATE TABLE parent(id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE child(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id));
        INSERT INTO parent VALUES(1, 'a'); INSERT INTO child VALUES(1, 1);''')
    con.close()
    return temp, path


def test_dependency_order_and_counts():
    temp, path = make_db()
    try:
        report = build_plan(path, {'parent': {'id', 'name'}, 'child': {'id', 'parent_id'}})
        assert report['copy_order'].index('parent') < report['copy_order'].index('child')
        assert report['tables']['child']['rows'] == 1
        assert report['all_nonempty_tables_structurally_mapped']
        assert not report['safe_to_execute_automatically']
    finally:
        temp.cleanup()


def test_missing_target_blocks_nonempty():
    temp, path = make_db()
    try:
        report = build_plan(path, {'parent': {'id', 'name'}})
        assert report['blocked_nonempty_tables'] == ['child']
    finally:
        temp.cleanup()


def test_missing_column_blocks_nonempty():
    temp, path = make_db()
    try:
        report = build_plan(path, {'parent': {'id'}, 'child': {'id', 'parent_id'}})
        assert 'parent' in report['blocked_nonempty_tables']
    finally:
        temp.cleanup()


def test_source_is_not_modified():
    temp, path = make_db()
    try:
        before = path.read_bytes()
        build_plan(path, {})
        assert path.read_bytes() == before
    finally:
        temp.cleanup()
