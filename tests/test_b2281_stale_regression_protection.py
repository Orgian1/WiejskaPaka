"""Reports must not certify tests that have changed since execution."""
import hashlib
import json
import pytest
from scripts.aggregate_full_regression import aggregate


def test_stale_report_rejected_after_test_changes(tmp_path):
    root = tmp_path / 'project'
    directory = root / 'tests'
    directory.mkdir(parents=True)
    target = directory / 'test_example.py'
    original = b'def test_example(): assert True\n'
    target.write_bytes(original)
    report = tmp_path / 'report.json'
    report.write_text(json.dumps({'complete': True, 'executed': 1, 'planned': 1,
        'results': [{'file': target.name, 'sha256': hashlib.sha256(original).hexdigest(), 'returncode': 0}]}))
    assert aggregate(root, [report])['success']
    target.write_text('def test_example(): assert False\n')
    with pytest.raises(ValueError, match='Stale'):
        aggregate(root, [report])

def test_old_report_without_checksum_is_not_trusted(tmp_path):
    root = tmp_path / 'project'
    directory = root / 'tests'
    directory.mkdir(parents=True)
    (directory / 'test_example.py').write_text('def test_example(): assert True\n')
    report = tmp_path / 'legacy.json'
    report.write_text(json.dumps({'complete': True, 'executed': 1, 'planned': 1,
        'results': [{'file': 'test_example.py', 'returncode': 0}]}))
    with pytest.raises(ValueError, match='Stale'):
        aggregate(root, [report])
