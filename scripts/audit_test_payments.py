"""Read-only local SQLite audit. Never connects to Neon/PostgreSQL."""
import argparse
from contextlib import closing
import json
import sqlite3
from pathlib import Path
from backend.payment_integrity import audit_payment_integrity


def main():
    parser = argparse.ArgumentParser(description='Audyt wyłącznie lokalnej symulacji płatności')
    parser.add_argument('--sqlite', required=True, help='Ścieżka do istniejącej lokalnej bazy SQLite')
    args = parser.parse_args()
    path = Path(args.sqlite).resolve()
    if not path.is_file():
        parser.error('Plik SQLite nie istnieje; audyt nie utworzy nowej bazy')
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as con:
            con.row_factory = sqlite3.Row
            con.execute('BEGIN')
            result = audit_payment_integrity(con)
    except sqlite3.DatabaseError:
        print(json.dumps({'ok': False, 'complete': False, 'error': 'AUDIT_UNAVAILABLE'}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
