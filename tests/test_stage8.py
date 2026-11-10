import os
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.pg_adapter import translate_sql

def test_sql_translation_preserves_quoted_question_marks():
    assert translate_sql("SELECT '?' AS literal, id FROM products WHERE id=?") == "SELECT '?' AS literal, id FROM products WHERE id=%s"

def test_postgres_transaction_begin_is_adapter_noop():
    assert translate_sql('BEGIN IMMEDIATE') is None

def test_atomic_stock_decrement_under_contention(tmp_path):
    path = tmp_path / 'inventory.db'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE products (id INTEGER PRIMARY KEY, stock INTEGER NOT NULL CHECK(stock >= 0))')
        con.execute('INSERT INTO products VALUES (1, 1)')
    barrier = threading.Barrier(2)
    def reserve(_):
        with sqlite3.connect(path, timeout=5) as con:
            barrier.wait()
            result = con.execute('UPDATE products SET stock=stock-1 WHERE id=1 AND stock>=1')
            return result.rowcount
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sorted(results) == [0, 1]
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT stock FROM products WHERE id=1').fetchone()[0] == 0
