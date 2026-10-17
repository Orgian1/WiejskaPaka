"""Read-only inventory of SQLite data and PostgreSQL migration SQL coverage.

This is a preflight report, NOT a data migrator or proof of schema equivalence.
"""
import argparse
import json
import re
import sqlite3
from pathlib import Path

CREATE = re.compile(r'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:"?public"?\.)?"?([a-z_][a-z_0-9]*)"?\s*\(', re.I)


def declared_tables(sql_dir):
    result = set()
    files = sorted(Path(sql_dir).glob('*.sql'))
    for path in files:
        result.update(m.group(1).lower() for m in CREATE.finditer(path.read_text(encoding='utf-8')))
    return result


def inventory(sqlite_path, sql_dir):
    source = Path(sqlite_path).resolve()
    if not source.is_file():
        raise ValueError('Nie znaleziono źródłowej bazy SQLite')
    con = sqlite3.connect(f'file:{source}?mode=ro', uri=True)
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        destination = declared_tables(sql_dir)
        records = []
        for table in tables:
            escaped = table.replace('"', '""')
            count = con.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0]
            records.append({'table': table, 'rows': count, 'postgres_table_declared': table.lower() in destination})
        missing = [r['table'] for r in records if r['rows'] > 0 and not r['postgres_table_declared']]
        return {
            'sqlite_integrity': con.execute('PRAGMA integrity_check').fetchone()[0],
            'sqlite_foreign_key_errors': len(con.execute('PRAGMA foreign_key_check').fetchall()),
            'tables': records,
            'nonempty_tables_missing_pg_declaration': missing,
            'safe_to_run_legacy_migrator': False,
            'note': 'Deklaracja tabeli nie potwierdza zgodności kolumn, typów ani pełnej migracji danych.'
        }
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', required=True)
    parser.add_argument('--sql-dir', default=str(Path(__file__).parent))
    args = parser.parse_args()
    report = inventory(args.sqlite, args.sql_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['sqlite_integrity'] != 'ok' or report['sqlite_foreign_key_errors'] or report['nonempty_tables_missing_pg_declaration']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
