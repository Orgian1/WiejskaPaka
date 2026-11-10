import json
import subprocess
import sys
from pathlib import Path

from scripts.analyze_regression_report import analyze

ROOT = Path(__file__).resolve().parents[1]


def report(groups=None, **kwargs):
    data = {'complete': True, 'start_batch': 1, 'only_batch': None,
            'batches': [{'batch': 1, 'files': ['test_a.py'], 'returncode': 0, 'seconds': 0.1}] if groups is None else groups}
    data.update(kwargs)
    return data


def test_valid_complete():
    assert analyze(report())['complete']


def test_empty_complete_rejected():
    assert 'false_complete_claim' in analyze(report([]))['issues']


def test_root_type_rejected():
    assert not analyze([])['valid']


def test_missing_batches():
    assert not analyze({'complete': False})['valid']


def test_missing_complete_flag():
    assert not analyze({'batches': []})['valid']


def test_complete_string_rejected():
    assert not analyze(report(complete='true'))['valid']


def test_failed_batch_cannot_be_complete():
    x = report()['batches']; x[0]['returncode'] = 1
    assert not analyze(report(x))['complete']


def test_timeout_count():
    x = report()['batches']; x[0].update(returncode=None, timeout=True)
    assert analyze(report(x, complete=False))['timed_out'] == 1


def test_timeout_complete_rejected():
    x = report()['batches']; x[0].update(returncode=None, timeout=True)
    assert not analyze(report(x))['complete']


def test_missing_returncode():
    x = report()['batches']; del x[0]['returncode']
    assert not analyze(report(x))['valid']


def test_bool_returncode_rejected():
    x = report()['batches']; x[0]['returncode'] = False
    assert not analyze(report(x))['valid']


def test_string_returncode_rejected():
    x = report()['batches']; x[0]['returncode'] = '0'
    assert not analyze(report(x))['valid']


def test_duplicate_batch_number():
    x = report()['batches']; x.append(dict(x[0]))
    assert not analyze(report(x))['valid']


def test_zero_batch_number():
    x = report()['batches']; x[0]['batch'] = 0
    assert not analyze(report(x))['valid']


def test_boolean_batch_number():
    x = report()['batches']; x[0]['batch'] = True
    assert not analyze(report(x))['valid']


def test_gap_in_complete_batches():
    x = report()['batches']; x.append(dict(x[0], batch=3))
    assert not analyze(report(x))['complete']


def test_partial_start_cannot_be_complete():
    assert not analyze(report(start_batch=2))['complete']


def test_only_batch_cannot_be_complete():
    assert not analyze(report(only_batch=1))['complete']


def test_missing_files():
    x = report()['batches']; x[0]['files'] = []
    assert not analyze(report(x))['valid']


def test_path_traversal_files():
    x = report()['batches']; x[0]['files'] = ['../test_a.py']
    assert not analyze(report(x))['valid']


def test_windows_path_files():
    x = report()['batches']; x[0]['files'] = ['test_..\\secret.py']
    assert not analyze(report(x))['valid']


def test_non_test_file():
    x = report()['batches']; x[0]['files'] = ['production.py']
    assert not analyze(report(x))['valid']


def test_negative_duration():
    x = report()['batches']; x[0]['seconds'] = -1
    assert not analyze(report(x))['valid']


def test_nan_duration():
    x = report()['batches']; x[0]['seconds'] = float('nan')
    assert not analyze(report(x))['valid']


def test_string_duration():
    x = report()['batches']; x[0]['seconds'] = '1'
    assert not analyze(report(x))['valid']


def test_non_object_group():
    assert not analyze(report([None]))['valid']


def test_failed_count():
    x = report()['batches']; x[0]['returncode'] = 2
    assert analyze(report(x, complete=False))['failed'] == 1


def test_partial_valid_but_not_complete():
    result = analyze(report(complete=False))
    assert result['valid'] and not result['complete']


def test_cli_valid(tmp_path):
    p = tmp_path / 'report.json'; p.write_text(json.dumps(report()), encoding='utf-8')
    run = subprocess.run([sys.executable, str(ROOT / 'scripts/analyze_regression_report.py'), str(p), '--json'], capture_output=True, text=True)
    assert run.returncode == 0 and json.loads(run.stdout)['complete']


def test_cli_incomplete(tmp_path):
    p = tmp_path / 'report.json'; p.write_text(json.dumps(report(complete=False)), encoding='utf-8')
    run = subprocess.run([sys.executable, str(ROOT / 'scripts/analyze_regression_report.py'), str(p)], capture_output=True, text=True)
    assert run.returncode == 1


def test_cli_invalid_json(tmp_path):
    p = tmp_path / 'report.json'; p.write_text('{broken', encoding='utf-8')
    run = subprocess.run([sys.executable, str(ROOT / 'scripts/analyze_regression_report.py'), str(p), '--json'], capture_output=True, text=True)
    assert run.returncode == 1 and not json.loads(run.stdout)['valid']
