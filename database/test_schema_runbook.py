"""Generate a human-reviewable, non-executing psql runbook for a fresh test DB."""
from pathlib import Path
from database.schema_lock import verify_lock
from database.test_schema_safety import check_atomic_test_scripts
from database.test_schema_manifest import BASE, UPGRADES, required_startup_tables_covered


def build_runbook(root=None, lock_path=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    verified = verify_lock(root, lock_path)
    check_atomic_test_scripts(root)
    missing = required_startup_tables_covered(root)
    if missing:
        raise ValueError('Startup tables missing from migration scripts: ' + ', '.join(missing))
    names = (BASE, *UPGRADES)
    for name in names:
        if (root / name).resolve().parent != root.resolve():
            raise ValueError('Unsafe SQL path')
    lines = [
        '-- REVIEW ONLY: do not run against production or existing data.',
        '-- Create an EMPTY dedicated test database first; use a non-superuser role.',
        '-- Run with psql -X -v ON_ERROR_STOP=1 -1 -d "$WP_TEST_DATABASE_URL" -f runbook.sql',
        '-- -1 wraps the full script in one transaction; do not use if scripts contain nontransactional commands.',
    ]
    for name in names:
        lines.append('\\ir ' + name)
    return {'sql': '\n'.join(lines) + '\n', 'verified_files': verified['verified_files'],
            'execution_performed': False, 'missing_startup_tables': missing}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='Write reviewed psql include plan; never execute it')
    args = parser.parse_args()
    result = build_runbook()
    output = Path(args.output)
    if output.parent.resolve() != Path(__file__).resolve().parent:
        parser.error('Save the runbook in the database directory so relative includes resolve')
    if output.exists():
        parser.error('Output exists; refusing to overwrite')
    output.write_text(result['sql'], encoding='utf-8')
    print('Generated offline plan for', result['verified_files'], 'verified SQL files; no SQL executed')


if __name__ == '__main__':
    main()
