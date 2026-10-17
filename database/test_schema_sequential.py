"""Offline, non-atomic migration checklist for a NEW disposable test database.

Never run on existing databases. Each original file controls its own transaction;
a failure requires destroying and recreating the disposable database.
"""
from pathlib import Path
from database.schema_lock import verify_lock
from database.test_schema_manifest import BASE, UPGRADES, required_startup_tables_covered
from database.test_schema_safety import _without_comments_and_literals, FORBIDDEN
import re


def build_sequential_plan(root=None, lock_path=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    verified = verify_lock(root, lock_path)
    missing = required_startup_tables_covered(root)
    if missing:
        raise ValueError('Startup tables missing: ' + ', '.join(missing))
    names = (BASE, *UPGRADES)
    for name in names:
        if (root / name).resolve().parent != root.resolve():
            raise ValueError('Unsafe migration path')
        sql = (root / name).read_text(encoding='utf-8')
        clean = _without_comments_and_literals(sql)
        if re.search(r'^\s*\\', clean, re.M):
            raise ValueError('psql meta-command in ' + name)
        # No database switches or out-of-transaction commands. The original
        # BEGIN/COMMIT are allowed because each file is run separately.
        forbidden = re.compile(r'\b(?:CREATE\s+DATABASE|DROP\s+DATABASE|ALTER\s+SYSTEM|VACUUM|CREATE\s+(?:UNIQUE\s+)?INDEX\s+CONCURRENTLY|DROP\s+INDEX\s+CONCURRENTLY|REINDEX\s+CONCURRENTLY)\b', re.I)
        if forbidden.search(clean):
            raise ValueError('Unsupported migration statement in ' + name)
        # Do not attempt to parse plpgsql BEGIN within dollar-quoted bodies.
        # Top-level BEGIN/COMMIT must be paired and surround the entire file.
        statements = [line.strip().upper() for line in clean.splitlines() if line.strip().upper() in {'BEGIN;', 'COMMIT;', 'ROLLBACK;', 'START TRANSACTION;'}]
        if statements != ['BEGIN;', 'COMMIT;'] and statements:
            raise ValueError('Unexpected transaction boundaries in ' + name)
    lines = [
        '# REVIEW ONLY — NEW EMPTY DISPOSABLE TEST DATABASE, NEVER PRODUCTION.',
        '# Verify WP_TEST_DATABASE_URL points to a newly created, empty test database.',
        '# No global transaction: each file may commit independently.',
        '# On ANY failure, STOP. Destroy/recreate disposable DB; never resume midway.',
        '# Commands must be run by a human in a secure shell, from project root directory.',
        'set -e',
        ': "${WP_TEST_DATABASE_URL:?Missing dedicated test database URL}"',
        'export WP_TEST_DATABASE_URL',
        'python -m database.validate_migration_target',
        'cd database',
    ]
    for name in names:
        lines.append('psql -X -v ON_ERROR_STOP=1 -d "$WP_TEST_DATABASE_URL" -f ' + name)
    lines.extend(['cd ..', 'python -m database.verify_migrated_schema'])
    return {'script': '\n'.join(lines) + '\n', 'verified_files': verified['verified_files'],
            'execution_performed': False, 'atomic': False, 'missing_startup_tables': missing}
