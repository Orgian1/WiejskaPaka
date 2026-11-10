"""Conservative offline safety gate for a single-transaction PostgreSQL test runbook.

Not a SQL parser and not a substitute for execution on disposable PostgreSQL.
"""
import re
from pathlib import Path

from database.test_schema_manifest import BASE, UPGRADES

# Statements that cannot safely be included in a single atomic provisioning transaction,
# or that could switch targets / invoke external processes through psql.
FORBIDDEN = re.compile(
    r'\b(?:CREATE\s+DATABASE|DROP\s+DATABASE|ALTER\s+SYSTEM|'
    r'VACUUM|CREATE\s+(?:UNIQUE\s+)?INDEX\s+CONCURRENTLY|'
    r'DROP\s+INDEX\s+CONCURRENTLY|REINDEX\s+CONCURRENTLY|'
    r'BEGIN|START\s+TRANSACTION|COMMIT|ROLLBACK|'
    r'PREPARE\s+TRANSACTION|COMMIT\s+PREPARED|ROLLBACK\s+PREPARED)\b',
    re.IGNORECASE,
)


def _without_comments_and_literals(sql):
    """Remove common SQL comments and quoted literals while retaining newlines."""
    pattern = re.compile(r"--[^\n]*|/\*[\s\S]*?\*/|'(?:''|[^'])*'|\$([A-Za-z_][A-Za-z_0-9]*|)\$[\s\S]*?\$\1\$", re.I)
    return pattern.sub(lambda m: '\n' * m.group().count('\n') + ' ', sql)


def check_atomic_test_scripts(root):
    root = Path(root)
    problems = []
    for name in (BASE, *UPGRADES):
        sql = (root / name).read_text(encoding='utf-8')
        clean = _without_comments_and_literals(sql)
        if re.search(r'^\s*\\', clean, flags=re.M):
            problems.append(f'{name}: psql meta-command')
        if FORBIDDEN.search(clean):
            problems.append(f'{name}: non-atomic or transaction-control statement')
    if problems:
        raise ValueError('Unsafe atomic migration plan: ' + '; '.join(problems))
    return len((BASE, *UPGRADES))
