"""Offline migration from local SQLite to empty PostgreSQL.

Requirements: pip install psycopg[binary]; apply postgres_schema.sql first.
Usage: python -m database.migrate_sqlite_to_postgres --sqlite PATH --dsn-env WP_POSTGRES_DSN --execute
Without --execute performs SQLite validation and prints row counts only.
Stop writes to SQLite before migrating. Never expose DB passwords in command line.
"""
import argparse
import os
import sqlite3
from pathlib import Path

TABLES = ('users', 'login_attempts', 'sessions', 'farmer_profiles',
          'products', 'pickup_points', 'orders', 'order_locations')
IDENTITY = ('users', 'products', 'pickup_points', 'orders')

def read_source(path):
    if not Path(path).is_file():
        raise ValueError('Nie znaleziono bazy SQLite')
    con = sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise ValueError(f'SQLite integrity_check: {integrity}')
        fk_errors = con.execute('PRAGMA foreign_key_check').fetchall()
        if fk_errors:
            raise ValueError(f'Błędne klucze obce: {len(fk_errors)}')
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = set(TABLES) - tables
        if missing:
            raise ValueError(f'Brak tabel: {sorted(missing)}')
        # Nie wolno zgubić danych z modułów dodanych po pierwszym schemacie.
        # Ten migrator przenosi WYŁĄCZNIE TABLES; inne niepuste tabele wymagają
        # osobnej, kompletnej migracji i walidacji schematu docelowego.
        ignored_system = {'sqlite_sequence', 'schema_migrations'}
        extra = sorted(tables - set(TABLES) - ignored_system)
        nonempty_extra = []
        for name in extra:
            escaped = name.replace('"', '""')
            count = con.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0]
            if count:
                nonempty_extra.append((name, count))
        if nonempty_extra:
            raise ValueError(
                'Migrator v1 nie obsługuje niepustych tabel dodatkowych; '
                f'ryzyko utraty danych: {nonempty_extra}. '
                'Wymagana pełna migracja wszystkich modułów.'
            )
        return {name:[dict(r) for r in con.execute(f'SELECT * FROM {name}')] for name in TABLES}
    finally:
        con.close()

def migrate(data, dsn):
    import psycopg
    from psycopg import sql
    with psycopg.connect(dsn) as con:
        with con.transaction():
            with con.cursor() as cur:
                cur.execute('SELECT version FROM schema_migrations')
                if cur.fetchall() != [(1,)]:
                    raise ValueError('Nieobsługiwana wersja schematu PostgreSQL')
                for table in TABLES:
                    cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)))
                    if cur.fetchone()[0] != 0:
                        raise ValueError(f'Tabela {table} nie jest pusta — przerwano migrację')
                for table in TABLES:
                    rows = data[table]
                    if not rows:
                        continue
                    cols = list(rows[0])
                    query = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
                        sql.Identifier(table),
                        sql.SQL(', ').join(map(sql.Identifier, cols)),
                        sql.SQL(', ').join(sql.Placeholder() for _ in cols))
                    cur.executemany(query, [tuple(row[c] for c in cols) for row in rows])
                for table in IDENTITY:
                    cur.execute(sql.SQL('SELECT setval(pg_get_serial_sequence(%s,%s), GREATEST(COALESCE((SELECT MAX(id) FROM {}),0),1), (SELECT COUNT(*)>0 FROM {}))').format(
                        sql.Identifier(table),sql.Identifier(table)), (table,'id'))
                for table in TABLES:
                    cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)))
                    if cur.fetchone()[0] != len(data[table]):
                        raise ValueError(f'Niezgodna liczba rekordów w {table}')
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite',required=True)
    parser.add_argument('--dsn-env',default='WP_POSTGRES_DSN')
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    data=read_source(args.sqlite)
    for table,rows in data.items():
        print(f'{table}: {len(rows)}')
    if not args.execute:
        print('DRY RUN — nie zmieniono żadnej bazy')
        return
    dsn=os.environ.get(args.dsn_env)
    if not dsn:
        raise SystemExit(f'Brak zmiennej środowiskowej {args.dsn_env}')
    migrate(data,dsn)
    print('Migracja zakończona; przed przełączeniem API uruchom testy integracyjne')

if __name__=='__main__':
    main()
