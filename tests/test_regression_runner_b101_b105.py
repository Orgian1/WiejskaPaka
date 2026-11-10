"""B/101–105: isolation, resume and failure-report regressions."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_regression_chunks import batches, run


def test_b101_batch_partition_does_not_drop_files():
    source = list(range(53))
    assert sum(batches(source, 12), []) == source


def test_b102_resume_starts_at_requested_batch(tmp_path):
    first = tmp_path / 'test_first.py'
    second = tmp_path / 'test_second.py'
    first.write_text('def test_bad(): assert False\n')
    second.write_text('def test_good(): assert True\n')
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[first, second], batch_size=1, start_batch=2, timeout=15, report=report) == 0
    result = json.loads(report.read_text())
    assert result['start_batch'] == 2
    assert [entry['batch'] for entry in result['batches']] == [2]


def test_b103_stop_on_failure_preserves_diagnostics(tmp_path):
    first = tmp_path / 'test_first.py'
    second = tmp_path / 'test_second.py'
    first.write_text('def test_bad(): assert False\n')
    second.write_text('def test_good(): assert True\n')
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[first, second], batch_size=1, timeout=15, report=report, stop_on_failure=True) == 1
    result = json.loads(report.read_text())
    assert result['complete'] is False
    assert len(result['batches']) == 1
    assert 'FAILED' in result['batches'][0]['output_tail']


def test_b104_invalid_resume_index_rejected(tmp_path):
    file = tmp_path / 'test_one.py'
    file.write_text('def test_ok(): assert True\n')
    import pytest
    with pytest.raises(ValueError):
        run(tmp_path, selected=[file], start_batch=0)


def test_b105_empty_batch_selection_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        run(tmp_path, selected=[])
