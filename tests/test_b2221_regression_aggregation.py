import json
import hashlib
from pathlib import Path
import pytest
from scripts.aggregate_full_regression import aggregate


def project(tmp_path):
    root = tmp_path / 'project'
    (root / 'tests').mkdir(parents=True)
    for name in ('test_alpha.py', 'test_beta.py'):
        (root / 'tests' / name).write_text('def test_ok(): assert True\n', encoding='utf-8', newline='\n')
    return root


def report(tmp_path, name, entries, complete=True):
    path = tmp_path / name
    path.write_text(json.dumps({'complete': complete, 'planned': len(entries),
                                'executed': len(entries), 'results': entries}))
    return path


def entry(name, code=0):
    return {'file': name, 'returncode': code,
            'sha256': hashlib.sha256(b'def test_ok(): assert True\n').hexdigest()}


def test_success_only_when_all_modules_covered(tmp_path):
    root = project(tmp_path)
    first = report(tmp_path, 'one.json', [entry('test_alpha.py')])
    second = report(tmp_path, 'two.json', [entry('test_beta.py')])
    assert not aggregate(root, [first])['success']
    result = aggregate(root, [first, second])
    assert result['success'] and result['passed'] == 2


def test_failures_reported(tmp_path):
    root = project(tmp_path)
    path = report(tmp_path, 'one.json', [entry('test_alpha.py', 1), entry('test_beta.py')])
    result = aggregate(root, [path])
    assert result['failed'] == 1 and result['failures'] == ['test_alpha.py']
    assert not result['success']


def test_duplicate_or_incomplete_rejected(tmp_path):
    root = project(tmp_path)
    first = report(tmp_path, 'one.json', [entry('test_alpha.py')])
    with pytest.raises(ValueError, match='Duplicate'):
        aggregate(root, [first, first])
    incomplete = report(tmp_path, 'incomplete.json', [entry('test_beta.py')], complete=False)
    with pytest.raises(ValueError, match='Incomplete'):
        aggregate(root, [first, incomplete])


def test_unknown_module_rejected(tmp_path):
    root = project(tmp_path)
    path = report(tmp_path, 'bad.json', [entry('test_unknown.py')])
    with pytest.raises(ValueError, match='Unknown'):
        aggregate(root, [path])
