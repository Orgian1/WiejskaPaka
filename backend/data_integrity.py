"""Odczytowy audyt integralności SQLite, bez modyfikacji bazy."""
import sqlite3
from pathlib import Path


def inspect_sqlite(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f'Brak pliku bazy: {path}')
    con = sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)
    try:
        con.execute('PRAGMA query_only=ON')
        integrity = [row[0] for row in con.execute('PRAGMA integrity_check').fetchall()]
        fk = [dict(zip(('table', 'rowid', 'parent', 'fkid'), row)) for row in con.execute('PRAGMA foreign_key_check').fetchall()]
        tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts = {name: con.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0] for name in tables}
        return {'ok': integrity == ['ok'] and not fk, 'integrity': integrity, 'foreign_key_violations': fk, 'row_counts': counts}
    finally:
        con.close()


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description='Odczytowy audyt integralności lokalnej bazy SQLite')
    parser.add_argument('database', help='Ścieżka do istniejącego pliku SQLite')
    args = parser.parse_args()
    report = inspect_sqlite(args.database)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
