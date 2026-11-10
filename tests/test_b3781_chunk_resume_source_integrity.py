"""A resumed chunk run must not trust green results from an older app revision."""
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_regression_chunks import run


def test_resume_rejects_changed_application(tmp_path):
    (tmp_path / 'backend').mkdir()
    app = tmp_path / 'backend' / 'app.py'
    app.write_text('VERSION = 1\n')
    test = tmp_path / 'test_sample.py'
    test.write_text('def test_ok(): assert True\n')
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[test], report=report, timeout=20) == 0
    old = json.loads(report.read_text())
    assert old['application_sha256']
    app.write_text('VERSION = 2\n')
    with pytest.raises(ValueError, match='zmieniono kod aplikacji'):
        run(tmp_path, selected=[test], report=report, timeout=20, resume=True)


def test_resume_accepts_unchanged_application(tmp_path):
    test = tmp_path / 'test_sample.py'
    test.write_text('def test_ok(): assert True\n')
    report = tmp_path / 'report.json'
    assert run(tmp_path, selected=[test], report=report, timeout=20) == 0
    assert run(tmp_path, selected=[test], report=report, timeout=20, resume=True) == 0
