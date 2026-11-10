"""B/121–130: regression-runner hardening; no live database or payments."""
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_regression_chunks import batches, run, write_report_atomic


def case(folder, name, expression='True'):
    p = folder / f'test_{name}.py'
    p.write_text(f'def test_{name}():\n    assert {expression}\n', encoding='utf-8')
    return p


def test_b121_invalid_timeout(tmp_path):
    with pytest.raises(ValueError, match='timeout'):
        run(tmp_path, selected=[case(tmp_path, 'one')], timeout=0)


def test_b122_invalid_batch_size():
    with pytest.raises(ValueError):
        batches([1], 0)


def test_b123_atomic_report_is_valid_json(tmp_path):
    path = tmp_path / 'reports' / 'result.json'
    write_report_atomic(path, {'complete': False, 'batches': []})
    assert json.loads(path.read_text())['complete'] is False
    assert not list(path.parent.glob('*.tmp'))


def test_b124_atomic_report_replaces_old(tmp_path):
    path = tmp_path / 'report.json'
    path.write_text('old')
    write_report_atomic(path, {'complete': True})
    assert json.loads(path.read_text()) == {'complete': True}


def test_b125_missing_tests(tmp_path):
    with pytest.raises(ValueError, match='No test files'):
        run(tmp_path, selected=[])


def test_b126_out_of_range_batch(tmp_path):
    with pytest.raises(ValueError, match='exceeds'):
        run(tmp_path, selected=[case(tmp_path, 'one')], only_batch=2)


def test_b127_failure_does_not_claim_completion(tmp_path):
    path = tmp_path / 'report.json'
    assert run(tmp_path, selected=[case(tmp_path, 'bad', 'False')], report=path, timeout=15) == 1
    assert json.loads(path.read_text())['complete'] is False


def test_b128_selected_batch_is_partial(tmp_path):
    path = tmp_path / 'report.json'
    tests = [case(tmp_path, 'a'), case(tmp_path, 'b')]
    assert run(tmp_path, selected=tests, batch_size=1, only_batch=1, report=path, timeout=15) == 0
    assert json.loads(path.read_text())['complete'] is False


def test_b129_full_pass_is_complete(tmp_path):
    path = tmp_path / 'report.json'
    assert run(tmp_path, selected=[case(tmp_path, 'good')], report=path, timeout=15) == 0
    assert json.loads(path.read_text())['complete'] is True


def test_b130_stop_on_failure(tmp_path):
    path = tmp_path / 'report.json'
    tests = [case(tmp_path, 'a', 'False'), case(tmp_path, 'b')]
    assert run(tmp_path, selected=tests, batch_size=1, stop_on_failure=True, report=path, timeout=15) == 1
    assert len(json.loads(path.read_text())['batches']) == 1
