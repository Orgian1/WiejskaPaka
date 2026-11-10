"""Regression: separate test modules must not share the SQLite database."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_regression_chunks import run


def test_modules_have_separate_databases(tmp_path):
    tests = tmp_path / 'tests'
    tests.mkdir()
    source = '''import os, sqlite3

def test_clean_database():
    con = sqlite3.connect(os.environ["WIEJSKAPAKA_DB"])
    con.execute("CREATE TABLE IF NOT EXISTS test_counter (n INTEGER)")
    assert con.execute("SELECT COUNT(*) FROM test_counter").fetchone()[0] == 0
    con.execute("INSERT INTO test_counter VALUES (1)")
    con.commit()
    con.close()
'''
    files = []
    for name in ('test_alpha.py', 'test_beta.py'):
        path = tests / name
        path.write_text(source, encoding='utf-8')
        files.append(path)
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=files, batch_size=2, timeout=20, report=report) == 0
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['complete'] is True
    assert len(data['batches'][0]['file_results']) == 2
    assert all(item['returncode'] == 0 for item in data['batches'][0]['file_results'])
