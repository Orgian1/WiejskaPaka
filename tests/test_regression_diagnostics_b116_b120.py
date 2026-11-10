"""B/116–120: real failure isolation and truthful batch diagnostics."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_regression_chunks import run


def _case(path, name, body):
    file = path / f'test_{name}.py'
    file.write_text(f'def test_{name}():\n    {body}\n', encoding='utf-8')
    return file


def test_b116_single_file_failure_report(tmp_path):
    broken = _case(tmp_path, 'broken', 'assert 1 == 2')
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[broken], batch_size=1, timeout=15, report=report) == 1
    data = json.loads(report.read_text())
    assert data['complete'] is False
    assert 'FAILED' in data['batches'][0]['output_tail']


def test_b117_timeout_includes_last_test_name(tmp_path):
    slow = tmp_path / 'test_slow.py'
    slow.write_text('import time\ndef test_wait():\n    print("BEFORE_SLEEP", flush=True)\n    time.sleep(4)\n')
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[slow], batch_size=1, timeout=2, report=report) == 1
    result = json.loads(report.read_text())['batches'][0]
    assert result['timeout'] is True
    assert 'test_slow.py' in result['files']


def test_b118_partial_success_is_not_full_completion(tmp_path):
    a = _case(tmp_path, 'a', 'assert True')
    b = _case(tmp_path, 'b', 'assert True')
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[a, b], batch_size=1, only_batch=2, timeout=15, report=report) == 0
    assert json.loads(report.read_text())['complete'] is False


def test_b119_full_success_is_marked_complete(tmp_path):
    a = _case(tmp_path, 'a', 'assert True')
    b = _case(tmp_path, 'b', 'assert True')
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[a, b], batch_size=1, timeout=15, report=report) == 0
    data = json.loads(report.read_text())
    assert data['complete'] is True and len(data['batches']) == 2


def test_b120_failure_does_not_stop_next_batch_by_default(tmp_path):
    a = _case(tmp_path, 'a', 'assert False')
    b = _case(tmp_path, 'b', 'assert True')
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[a, b], batch_size=1, timeout=15, report=report) == 1
    assert [r['returncode'] for r in json.loads(report.read_text())['batches']] == [1, 0]
