"""Raport regresji: kompletność przebiegu nie oznacza zaliczenia testów."""
import json
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_tests_per_file as runner


def test_report_marks_completed_failed_run(tmp_path):
    root = Path(__file__).resolve().parents[1]
    target = root / 'tests' / 'test_b501_shared_delivery.py'

    class Failed:
        returncode = 1
        stdout = '1 failed'
        stderr = ''

    report = tmp_path / 'report.json'
    with patch.object(runner.subprocess, 'run', return_value=Failed()):
        assert runner.run(root, selected=[target], report=report) == 1
    data = json.loads(report.read_text())
    assert data['complete'] is True
    assert data['success'] is False
    assert data['executed'] == data['planned'] == 1
    assert data['passed'] == 0 and data['failed'] == 1


def test_report_marks_successful_run(tmp_path):
    root = Path(__file__).resolve().parents[1]
    target = root / 'tests' / 'test_b501_shared_delivery.py'

    class Passed:
        returncode = 0
        stdout = '1 passed'
        stderr = ''

    report = tmp_path / 'report.json'
    with patch.object(runner.subprocess, 'run', return_value=Passed()):
        assert runner.run(root, selected=[target], report=report) == 0
    data = json.loads(report.read_text())
    assert data['complete'] is True and data['success'] is True
    assert data['passed'] == 1 and data['failed'] == 0
