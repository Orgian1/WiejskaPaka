"""Regression runner safety checks: partial results must never be called full success."""
import importlib.util
from pathlib import Path
import json
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_regression_chunks as runner


def test_b106_rejects_batch_past_end(tmp_path):
    with pytest.raises(ValueError, match='exceeds'):
        runner.run(ROOT, selected=[ROOT / 'tests' / 'test_ui_dom_contract.py'], start_batch=2)


def test_b107_rejects_invalid_single_batch(tmp_path):
    with pytest.raises(ValueError, match='positive'):
        runner.run(ROOT, selected=[ROOT / 'tests' / 'test_ui_dom_contract.py'], only_batch=0)


def test_b108_partial_run_is_not_full_success(tmp_path):
    file = tmp_path / 'test_sample.py'
    file.write_text('def test_ok(): assert True\n', encoding='utf-8')
    report = tmp_path / 'report.json'
    status = runner.run(tmp_path, selected=[file, file], batch_size=1, only_batch=2, timeout=20, report=report)
    assert status == 0
    data = json.loads(report.read_text())
    assert data['complete'] is False and len(data['batches']) == 1
    assert data['batches'][0]['returncode'] == 0


def test_b109_full_small_run_success(tmp_path):
    file = tmp_path / 'test_sample.py'
    file.write_text('def test_ok(): assert True\n', encoding='utf-8')
    report = tmp_path / 'report.json'
    status = runner.run(tmp_path, selected=[file], timeout=20, report=report)
    assert status == 0 and json.loads(report.read_text())['complete'] is True


def test_b110_failing_run_has_nonzero_status(tmp_path):
    file = tmp_path / 'test_sample.py'
    file.write_text('def test_bad(): assert False\n', encoding='utf-8')
    report = tmp_path / 'report.json'
    assert runner.run(tmp_path, selected=[file], timeout=20, report=report) != 0
    assert json.loads(report.read_text())['batches'][0]['returncode'] != 0
