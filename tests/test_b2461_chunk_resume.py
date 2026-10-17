import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_regression_chunks as runner


def make_files(tmp_path):
    folder = tmp_path / 'tests'
    folder.mkdir()
    files = [folder / 'test_one.py', folder / 'test_two.py']
    for file in files:
        file.write_text('def test_example(): assert True\n')
    return files


def test_resume_reuses_successful_partial_batch(tmp_path, monkeypatch):
    files = make_files(tmp_path)
    report = tmp_path / 'results.json'
    calls = []

    class Completed:
        returncode = 0
        stdout = 'passed'
        stderr = ''

    def fake_subprocess(cmd, **kwargs):
        calls.append(cmd[-1])
        return Completed()

    monkeypatch.setattr(runner.subprocess, 'run', fake_subprocess)
    assert runner.run(tmp_path, selected=files, batch_size=2, report=report) == 0
    assert len(calls) == 2
    assert runner.run(tmp_path, selected=files, batch_size=2, report=report, resume=True) == 0
    assert len(calls) == 2
    assert json.loads(report.read_text())['complete'] is True


def test_resume_rejects_modified_test(tmp_path, monkeypatch):
    files = make_files(tmp_path)
    report = tmp_path / 'results.json'

    class Completed:
        returncode = 0
        stdout = 'passed'
        stderr = ''

    monkeypatch.setattr(runner.subprocess, 'run', lambda *a, **kw: Completed())
    assert runner.run(tmp_path, selected=files, batch_size=2, report=report) == 0
    files[0].write_text('def test_example(): assert False\n')
    with pytest.raises(ValueError, match='zmieniono zestaw testów'):
        runner.run(tmp_path, selected=files, batch_size=2, report=report, resume=True)


def test_resume_retries_failed_module_only(tmp_path, monkeypatch):
    files = make_files(tmp_path)
    report = tmp_path / 'results.json'
    calls = []

    class Completed:
        def __init__(self, code):
            self.returncode = code
            self.stdout = 'result'
            self.stderr = ''

    def fake_subprocess(cmd, **kwargs):
        calls.append(cmd[-1])
        return Completed(1 if cmd[-1] == str(files[1]) and len(calls) <= 2 else 0)

    monkeypatch.setattr(runner.subprocess, 'run', fake_subprocess)
    assert runner.run(tmp_path, selected=files, batch_size=2, report=report) == 1
    assert runner.run(tmp_path, selected=files, batch_size=2, report=report, resume=True) == 0
    assert calls == [str(files[0]), str(files[1]), str(files[1])]
