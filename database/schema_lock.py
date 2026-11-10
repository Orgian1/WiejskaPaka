"""Offline immutable SQL checksum lock for manual test-database provisioning."""
import json
from pathlib import Path
from database.test_schema_manifest import build_manifest

LOCK = Path(__file__).with_name('test_schema_checksums.json')


def verify_lock(root=None, lock_path=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    lock_path = Path(lock_path) if lock_path is not None else LOCK
    try:
        expected = json.loads(lock_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ValueError('Missing or invalid schema checksum lock') from exc
    if not isinstance(expected, list) or not all(isinstance(x, dict) for x in expected):
        raise ValueError('Invalid schema checksum lock format')
    actual = build_manifest(root)
    if expected != actual:
        raise ValueError('SQL migration checksums differ from reviewed lock; review changes before updating lock')
    return {'verified_files': len(actual), 'checksums_match': True, 'execution_performed': False}
