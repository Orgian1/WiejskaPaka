import json
from pathlib import Path
import pytest
from database.schema_lock import verify_lock
from database.test_schema_manifest import BASE, UPGRADES, build_manifest


def test_lock_matches_reviewed_sql():
    assert verify_lock()['verified_files'] == len(UPGRADES) + 1


def test_changed_sql_is_rejected(tmp_path):
    source = Path(__file__).resolve().parents[1] / 'database'
    for name in (BASE, *UPGRADES):
        (tmp_path / name).write_bytes((source / name).read_bytes())
    (tmp_path / BASE).write_text((tmp_path / BASE).read_text() + '\n-- changed\n')
    with pytest.raises(ValueError, match='checksums differ'):
        verify_lock(tmp_path)


def test_missing_or_invalid_lock_is_rejected(tmp_path):
    with pytest.raises(ValueError, match='Missing or invalid'):
        verify_lock(lock_path=tmp_path / 'missing.json')
    lock = tmp_path / 'bad.json'
    lock.write_text('{bad')
    with pytest.raises(ValueError, match='Missing or invalid'):
        verify_lock(lock_path=lock)


def test_order_change_is_rejected(tmp_path):
    lock = tmp_path / 'lock.json'
    entries = build_manifest()
    entries[0], entries[1] = entries[1], entries[0]
    lock.write_text(json.dumps(entries))
    with pytest.raises(ValueError, match='checksums differ'):
        verify_lock(lock_path=lock)
