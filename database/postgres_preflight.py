"""Read-only SQLite -> live PostgreSQL structural preflight.

No data is copied. Does not prove semantic/type equivalence or migration safety.
Set WP_POSTGRES_DSN to a disposable test PostgreSQL database.
"""
import argparse
import json
import os
import sqlite3
from pathlib import Path


def source_structure(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('Brak bazy SQLite')
    con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    try:
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Uszkodzona baza SQLite')
        if con.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Naruszone klucze obce SQLite')
        result = {}
        for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            quoted = '"' + table.replace('"', '""') + '"'
            count = con.execute(f'SELECT count(*) FROM {quoted}').fetchone()[0]
            columns = {r[1] for r in con.execute(f'PRAGMA table_info({quoted})')}
            result[table] = {'rows': count, 'columns': sorted(columns)}
        return result
    finally:
        con.close()


def destination_structure(dsn):
    import psycopg
    with psycopg.connect(dsn) as con:
        with con.cursor() as cur:
            cur.execute("""SELECT c.table_name, c.column_name
                           FROM information_schema.columns c
                           JOIN information_schema.tables t
                             ON t.table_schema = c.table_schema
                            AND t.table_name = c.table_name
                           WHERE c.table_schema = current_schema()
                             AND t.table_type = 'BASE TABLE' """)
            result = {}
            for table, column in cur.fetchall():
                result.setdefault(table, set()).add(column)
            return result


def compare(source, destination):
    """Only source tables with data block migration; empty tables are reported too."""
    differences = []
    for table, info in sorted(source.items()):
        target = destination.get(table)
        if target is None:
            differences.append({'table': table, 'rows': info['rows'], 'problem': 'missing_table', 'blocking': info['rows'] > 0})
            continue
        missing = sorted(set(info['columns']) - set(target))
        if missing:
            differences.append({'table': table, 'rows': info['rows'], 'problem': 'missing_columns', 'columns': missing, 'blocking': info['rows'] > 0})
    return {'safe_for_automatic_migration': False,
            'structural_preflight_passed': not any(item['blocking'] for item in differences),
            'differences': differences,
            'warning': 'Zgodność nazw kolumn nie gwarantuje zgodności typów, ograniczeń ani migracji danych.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', required=True)
    parser.add_argument('--dsn-env', default='WP_POSTGRES_DSN')
    args = parser.parse_args()
    dsn = os.getenv(args.dsn_env)
    if not dsn:
        parser.error(f'Brak zmiennej {args.dsn_env}; nie wykonano testu PostgreSQL')
    report = compare(source_structure(args.sqlite), destination_structure(dsn))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['structural_preflight_passed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
