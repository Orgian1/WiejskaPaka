from pathlib import Path
import pytest
from database.test_schema_sequential import build_sequential_plan
from database.test_schema_manifest import BASE, UPGRADES


def test_real_plan_lists_all_scripts_without_false_atomicity():
    plan = build_sequential_plan()
    assert plan['execution_performed'] is False
    assert plan['atomic'] is False
    assert plan['verified_files'] == 23
    assert '-1 ' not in plan['script']
    assert 'set -e' in plan['script']
    assert 'Destroy/recreate' in plan['script']
    assert [line.rsplit(' -f ', 1)[-1] for line in plan['script'].splitlines() if line.startswith('psql ')] == [BASE, *UPGRADES]


def test_modified_file_rejected(tmp_path):
    root = Path(__file__).resolve().parents[1] / 'database'
    for name in (BASE, *UPGRADES):
        (tmp_path / name).write_bytes((root / name).read_bytes())
    (tmp_path / BASE).write_text('BEGIN;\nSELECT 1;\nCOMMIT;')
    with pytest.raises(ValueError, match='checksums differ'):
        build_sequential_plan(tmp_path)


def test_missing_files_rejected(tmp_path):
    with pytest.raises(ValueError):
        build_sequential_plan(tmp_path)
