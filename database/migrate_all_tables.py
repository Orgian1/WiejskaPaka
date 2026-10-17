"""Strict, offline SQLite -> disposable PostgreSQL migration.

Requires a pre-created schema and an EMPTY destination for all application tables.
Never point this tool at production. No schema creation or destructive commands.
"""
import argparse
import os
import sqlite3
from pathlib import Path

from database.migration_plan import build_plan
from database.postgres_preflight import destination_structure


def validate_plan(plan):
    if plan['blocked_nonempty_tables']:
        raise ValueError('Brak mapowania tabel z danymi: ' + ', '.join(plan['blocked_nonempty_tables']))
    for name, entry in plan['tables'].items():
        if entry['blockers']:
            raise ValueError(f'Tabela {name}: {entry["blockers"]}')
    if len(plan['copy_order']) != len(plan['tables']):
        raise ValueError('Cykl zależności — wymagana ręczna migracja')
    if 'schema_migrations' in plan['tables'] and plan['tables']['schema_migrations']['rows']:
        raise ValueError('schema_migrations wymaga osobnej obsługi wersji schematu')
    return True


def destination_tables_to_check(structure, source_tables):
    """Check every destination application table, including tables absent in SQLite.

    A pre-populated destination could otherwise be mistaken for a clean test
    database merely because those tables do not occur in the source snapshot.
    """
    return sorted(set(structure) | set(source_tables))


def copy_all(sqlite_path, dsn, *, confirmed=False):
    if not confirmed:
        raise ValueError('Wymagane jawne potwierdzenie --execute')
    import psycopg
    from psycopg import sql

    path = Path(sqlite_path).resolve()
    if not path.is_file():
        raise ValueError('Brak źródłowej bazy SQLite')
    source = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    try:
        # Consistent source snapshot for planning AND reading.
        source.execute('BEGIN')
        if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Baza SQLite jest uszkodzona')
        if source.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Błędne klucze obce SQLite')
        with psycopg.connect(dsn) as target:
            with target.transaction():
                with target.cursor() as cur:
                    cur.execute('SET LOCAL lock_timeout = %s', ('5s',))
                    cur.execute('SET LOCAL statement_timeout = %s', ('120s',))
                    structure = destination_structure_from_cursor(cur)
                    plan = build_plan(path, structure, source_connection=source)
                    validate_plan(plan)
                    tables = plan['copy_order']
                    # Lock destination to prevent concurrent inserts while verifying emptiness.
                    for table in destination_tables_to_check(structure, tables):
                        cur.execute(sql.SQL('LOCK TABLE {} IN EXCLUSIVE MODE').format(sql.Identifier(table)))
                        cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)))
                        if cur.fetchone()[0]:
                            raise ValueError(f'Baza docelowa nie jest pusta: {table}')
                    result = {}
                    for table in tables:
                        quoted = '"' + table.replace('"', '""') + '"'
                        records = source.execute(f'SELECT * FROM {quoted}').fetchall()
                        columns = plan['tables'][table]['columns']
                        if len(records) != plan['tables'][table]['rows']:
                            raise ValueError(f'Źródło zmieniło się podczas migracji: {table}')
                        if records:
                            query = sql.SQL('INSERT INTO {} ({}) {} VALUES ({})').format(
                                sql.Identifier(table),
                                sql.SQL(', ').join(map(sql.Identifier, columns)),
                                sql.SQL('OVERRIDING SYSTEM VALUE') if 'id' in columns else sql.SQL(''),
                                sql.SQL(', ').join(sql.Placeholder() for _ in columns))
                            cur.executemany(query, [tuple(row[col] for col in columns) for row in records])
                        cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)))
                        count = cur.fetchone()[0]
                        if count != len(records):
                            raise ValueError(f'Niezgodna liczba rekordów: {table}')
                        result[table] = count
                        if 'id' in columns:
                            cur.execute('SELECT pg_get_serial_sequence(%s, %s)', (table, 'id'))
                            seq = cur.fetchone()[0]
                            if seq:
                                cur.execute(sql.SQL('SELECT max(id) FROM {}').format(sql.Identifier(table)))
                                max_id = cur.fetchone()[0]
                                if max_id is not None:
                                    cur.execute('SELECT setval(%s::regclass, %s, true)', (seq, max_id))
                    # Force deferred FK constraints to be checked before reporting success.
                    cur.execute('SET CONSTRAINTS ALL IMMEDIATE')
                    # PostgreSQL validates FK constraints at INSERT or COMMIT.
                    # Any error rolls back ALL inserted rows.
                    return result
    finally:
        source.close()


def destination_structure_from_cursor(cur):
    cur.execute('''SELECT c.table_name, c.column_name
                   FROM information_schema.columns c
                   JOIN information_schema.tables t
                     ON t.table_schema = c.table_schema
                    AND t.table_name = c.table_name
                   WHERE c.table_schema = current_schema()
                     AND t.table_type = 'BASE TABLE' ''')
    result = {}
    for table, column in cur.fetchall():
        result.setdefault(table, set()).add(column)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', required=True)
    parser.add_argument('--dsn-env', default='WP_POSTGRES_DSN')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    dsn = os.getenv(args.dsn_env)
    if not dsn:
        parser.error(f'Brak {args.dsn_env}; wymagana WYŁĄCZNIE testowa baza PostgreSQL')
    plan = build_plan(args.sqlite, destination_structure(dsn))
    validate_plan(plan)
    print('Tabele do przeniesienia:', {k: v['rows'] for k, v in plan['tables'].items()})
    if not args.execute:
        print('DRY RUN — bez zapisu; użyj --execute tylko na pustej TESTOWEJ bazie')
        return
    result = copy_all(args.sqlite, dsn, confirmed=True)
    print('Przeniesiono:', result)
    print('Nadal wymagane testy integracyjne i porównanie danych przed wdrożeniem')


if __name__ == '__main__':
    main()
