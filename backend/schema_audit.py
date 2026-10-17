"""Audyt zgodności tabel SQLite i skryptów PostgreSQL (bez zmian danych)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = re.compile(r'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?([a-z_][a-z_0-9]*)', re.I)


def defined_tables(paths):
    names = set()
    for path in paths:
        names.update(match.lower() for match in TABLE.findall(Path(path).read_text(encoding='utf-8')))
    return names


def audit_schema(root=ROOT):
    root = Path(root)
    backend_files = list((root / 'backend').glob('*.py'))
    pg_files = [root / 'database' / 'postgres_schema.sql', *sorted((root / 'database').glob('upgrade_*.sql'))]
    local = defined_tables(backend_files)
    postgres = defined_tables(pg_files)
    return {'sqlite_tables': sorted(local), 'postgres_tables': sorted(postgres),
            'missing_in_postgres': sorted(local - postgres), 'extra_in_postgres': sorted(postgres - local)}


def verify_live_postgres(dsn, root=ROOT):
    """Tylko odczyt metadanych; nigdy nie inicjuje ani nie zmienia bazy."""
    import psycopg
    audit = audit_schema(root)
    with psycopg.connect(dsn, connect_timeout=5) as con:
        with con.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
            actual = {row[0] for row in cur.fetchall()}
    audit['live_missing'] = sorted(set(audit['sqlite_tables']) - actual)
    audit['live_tables'] = sorted(actual)
    return audit


if __name__ == '__main__':
    import json
    import os
    import sys
    dsn = os.getenv('WP_AUDIT_POSTGRES_DSN')
    report = verify_live_postgres(dsn) if dsn else audit_schema()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(bool(report['missing_in_postgres'] or report.get('live_missing')))
