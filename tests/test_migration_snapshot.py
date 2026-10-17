import sqlite3
import tempfile
import unittest
from pathlib import Path
from database.migration_snapshot import snapshot, compare


class MigrationSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.sqlite'
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT, payload BLOB)')
            db.execute('INSERT INTO people VALUES (1, ?, ?)', ('PRYWATNE DANE', b'xyz'))

    def test_stable_and_no_pii(self):
        first = snapshot(self.path)
        self.assertEqual(first, snapshot(self.path))
        self.assertNotIn('PRYWATNE DANE', str(first))
        self.assertEqual(first['tables']['people']['rows'], 1)

    def test_changed_row_detected(self):
        first = snapshot(self.path)
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE people SET name=? WHERE id=1', ('zmiana',))
        self.assertEqual(compare(first, snapshot(self.path))['changed_tables'], ['people'])

    def test_added_table_detected(self):
        first = snapshot(self.path)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE extra (id INTEGER)')
        self.assertEqual(compare(first, snapshot(self.path))['changed_tables'], ['extra'])

    def test_missing_database_does_not_create(self):
        missing = Path(self.temp.name) / 'missing.sqlite'
        with self.assertRaises(ValueError):
            snapshot(missing)
        self.assertFalse(missing.exists())

    def test_corrupt_foreign_key_detected(self):
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE parent (id INTEGER PRIMARY KEY)')
            db.execute('CREATE TABLE child (pid INTEGER REFERENCES parent(id))')
            db.execute('INSERT INTO child VALUES (123)')
        with self.assertRaises(ValueError):
            snapshot(self.path)
