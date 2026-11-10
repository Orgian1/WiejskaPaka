"""Read-only migration planner. Never copies data or changes either database."""
import argparse
import json
import sqlite3
from pathlib import Path


def build_plan(sqlite_path, destination_columns, *, source_connection=None):
    path = Path(sqlite_path).resolve()
    if not path.is_file():
        raise ValueError('Źródłowa baza SQLite nie istnieje')
    con = source_connection if source_connection is not None else sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    try:
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Uszkodzona baza SQLite')
        if con.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Błędne powiązania kluczy obcych SQLite')
        names = sorted(r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        entries = {}
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [r[1] for r in con.execute(f'PRAGMA table_info({quoted})')]
            # A self-referencing FK is handled by the destination transaction;
            # other dependencies determine insertion order.
            dependencies = sorted({r[2] for r in con.execute(f'PRAGMA foreign_key_list({quoted})') if r[2] != name})
            rows = con.execute(f'SELECT count(*) FROM {quoted}').fetchone()[0]
            target = destination_columns.get(name)
            blockers = []
            if target is None:
                blockers.append('Brak tabeli docelowej')
            else:
                missing = sorted(set(columns) - set(target))
                if missing:
                    blockers.append('Brak kolumn docelowych: ' + ', '.join(missing))
            entries[name] = {'rows': rows, 'columns': columns, 'depends_on': dependencies,
                             'blockers': blockers, 'requires_copy': bool(rows)}
        # Topological ordering of SQLite foreign-key dependencies.
        pending = set(names)
        order = []
        while pending:
            ready = sorted(name for name in pending if not (set(entries[name]['depends_on']) & pending))
            if not ready:
                break
            order.extend(ready)
            pending.difference_update(ready)
        if pending:
            for name in pending:
                entries[name]['blockers'].append('Cykl zależności FK — potrzebna ręczna migracja')
        blocked = sorted(name for name, info in entries.items() if info['requires_copy'] and info['blockers'])
        return {'tables': entries, 'copy_order': order, 'blocked_nonempty_tables': blocked,
                'all_nonempty_tables_structurally_mapped': not blocked,
                'safe_to_execute_automatically': False,
                'warning': 'Plan nie przenosi danych. Należy dodatkowo zweryfikować typy, ograniczenia, sekwencje, dane i transakcje.'}
    finally:
        if source_connection is None:
            con.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', required=True)
    parser.add_argument('--dsn-env', default='WP_POSTGRES_DSN')
    args = parser.parse_args()
    import os
    from database.postgres_preflight import destination_structure
    dsn = os.environ.get(args.dsn_env)
    if not dsn:
        parser.error(f'Brak zmiennej {args.dsn_env} (testowa baza PostgreSQL)')
    report = build_plan(args.sqlite, destination_structure(dsn))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['blocked_nonempty_tables']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
