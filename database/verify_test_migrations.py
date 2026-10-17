"""Offline CLI gate for test PostgreSQL SQL files; never opens a DB connection."""
import argparse
import json
from pathlib import Path

from database.test_schema_manifest import BASE, UPGRADES, build_manifest, required_startup_tables_covered
from database.schema_lock import verify_lock


def verify(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    manifest = build_manifest(root)
    lock = verify_lock(root)
    declared = {BASE, *UPGRADES}
    actual = {p.name for p in root.glob('*.sql') if p.is_file()}
    untracked = sorted(actual - declared)
    missing_tables = required_startup_tables_covered(root)
    return {
        'ok': not untracked and not missing_tables,
        'files': manifest,
        'untracked_sql': untracked,
        'missing_startup_tables': missing_tables,
        'execution_performed': False,
        'checksum_lock': lock,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    try:
        result = verify(args.directory)
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc), 'execution_performed': False}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
