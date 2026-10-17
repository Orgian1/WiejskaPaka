"""A successful subprocess must not certify sources edited during a run."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_tests_per_file import run


@pytest.mark.parametrize('changed', ['application', 'test'])
def test_source_changes_invalidate_final_report(tmp_path, monkeypatch, changed):
    from types import SimpleNamespace
    import run_tests_per_file
    (tmp_path / 'backend').mkdir()
    application = tmp_path / 'backend/app.py'
    application.write_text('version = 1\n')
    (tmp_path / 'tests').mkdir()
    test = tmp_path / 'tests/test_sample.py'
    test.write_text('def test_ok(): assert True\n')

    def mutate(*args, **kwargs):
        target = application if changed == 'application' else test
        target.write_text(target.read_text() + '# edited during execution\n')
        return SimpleNamespace(returncode=0, stdout='1 passed', stderr='')

    monkeypatch.setattr(run_tests_per_file.subprocess, 'run', mutate)
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[test], report=report) == 1
    data = json.loads(report.read_text())
    assert data['complete'] is False and data['success'] is False
    assert data['invalid_reason'] == 'sources_changed_during_run'
