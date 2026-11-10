import hashlib
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_tests_per_file import run, application_fingerprint


def setup(tmp_path):
    folder = tmp_path / 'tests'
    folder.mkdir()
    first = folder / 'test_alpha.py'
    second = folder / 'test_beta.py'
    first.write_text('def test_ok(): assert True\n')
    second.write_text('def test_ok(): assert True\n')
    report = tmp_path / 'report.json'
    item = {'file': first.name, 'sha256': hashlib.sha256(first.read_bytes()).hexdigest(),
            'returncode': 0, 'seconds': 0.1, 'output_tail': '1 passed'}
    report.write_text(json.dumps({'planned': 2, 'executed': 1, 'complete': False, 'application_sha256': application_fingerprint(tmp_path), 'results': [item]}))
    return first, second, report


def test_resume_skips_verified_pass_and_runs_remaining(tmp_path, monkeypatch):
    first, second, report = setup(tmp_path)
    import run_tests_per_file
    class Result:
        returncode = 0
        stdout = '1 passed'
        stderr = ''
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command[-1])
        return Result()
    monkeypatch.setattr(run_tests_per_file.subprocess, 'run', fake_run)
    assert run(tmp_path, selected=[first, second], report=report, resume=True) == 0
    assert calls == [str(second)]
    data = json.loads(report.read_text())
    assert data['complete'] and data['passed'] == 2


def test_resume_rejects_changed_test(tmp_path):
    first, second, report = setup(tmp_path)
    first.write_text('def test_changed(): assert False\n')
    with pytest.raises(ValueError, match='Stale'):
        run(tmp_path, selected=[first, second], report=report, resume=True)


def test_resume_rejects_changed_plan(tmp_path):
    first, second, report = setup(tmp_path)
    with pytest.raises(ValueError, match='plan'):
        run(tmp_path, selected=[first], report=report, resume=True)


def test_resume_rejects_reordered_modules(tmp_path):
    first, second, report = setup(tmp_path)
    data = json.loads(report.read_text())
    data['results'][0]['file'] = second.name
    report.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='unexpected'):
        run(tmp_path, selected=[first, second], report=report, resume=True)


def test_resume_refresh_stale_reruns_changed_module(tmp_path, monkeypatch):
    first, second, report = setup(tmp_path)
    first.write_text('def test_updated(): assert True\n')
    import run_tests_per_file

    class Result:
        returncode = 0
        stdout = '1 passed'
        stderr = ''

    calls = []
    def fake_run(command, **kwargs):
        calls.append(command[-1])
        return Result()

    monkeypatch.setattr(run_tests_per_file.subprocess, 'run', fake_run)
    assert run(tmp_path, selected=[first, second], report=report,
               resume=True, refresh_stale=True) == 0
    assert calls == [str(first), str(second)]
    data = json.loads(report.read_text())
    assert data['success'] and data['passed'] == 2
    assert data['results'][0]['sha256'] == hashlib.sha256(first.read_bytes()).hexdigest()
