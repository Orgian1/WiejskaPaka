"""Per-file isolation regression runner safety tests."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_tests_per_file import run


def test_two_modules_with_same_database_record_do_not_collide(tmp_path):
    # Two independent test files use the same unique database key.
    # Both pass only if each module gets its own SQLite database.
    # Probe files belong to the temporary project, never the source tree.
    tests = tmp_path / 'tests'
    tests.mkdir()
    files = []
    try:
        for suffix in ('a', 'b'):
            path = tests / f'test_b1141_isolation_probe_{suffix}.py'
            path.write_text('''import os, sqlite3\ndef test_insert():\n    con = sqlite3.connect(os.environ["WIEJSKAPAKA_DB"])\n    con.execute("CREATE TABLE marker (id INTEGER PRIMARY KEY)")\n    con.execute("INSERT INTO marker VALUES (1)")\n    con.commit()\n    con.close()\n''', encoding='utf-8')
            files.append(path)
        report = tmp_path / 'report.json'
        assert run(tmp_path, selected=files, report=report) == 0
        assert json.loads(report.read_text())['complete'] is True
    finally:
        for path in files:
            path.unlink(missing_ok=True)


def test_runner_rejects_outside_files(tmp_path):
    path = tmp_path / 'test_unsafe.py'
    path.write_text('def test_ok(): pass')
    try:
        run(ROOT, selected=[path])
    except ValueError:
        pass
    else:
        raise AssertionError('Unsafe path accepted')


def test_failure_location_survives_long_private_diagnostics(tmp_path):
    import xml.etree.ElementTree as ET
    from run_tests_per_file import failure_locations
    tests=tmp_path/'tests';tests.mkdir()
    (tests/'test_probe.py').write_text('')
    suite=ET.Element('testsuite')
    case=ET.SubElement(suite,'testcase',name='private-name[private-address]')
    node=ET.SubElement(case,'failure')
    node.text='C:\\private\\test_probe.py:42: private-token\n'+('private-address '*1000)+'\ntest_unknown.py:99: ignored'
    path=tmp_path/'private.xml';ET.ElementTree(suite).write(path)
    result=failure_locations(path,tmp_path)
    assert result==[{'file':'test_probe.py','line':42}]
    assert 'private' not in json.dumps(result)
