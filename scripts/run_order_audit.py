"""Read-only offline order audit. Exit 0 clean, 1 issues, 2 operational failure."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.order_integrity import audit_orders


def run(db_path):
    path = Path(db_path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('Database path must be a regular file')
    uri = path.as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as con:
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA query_only=ON')
        result = audit_orders(con)
    return result


def save_atomic(path, payload):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.order_audit_', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, help='Existing SQLite database; opened read-only')
    parser.add_argument('--report', help='Optional JSON report destination')
    args = parser.parse_args(argv)
    try:
        result = run(args.database)
        if args.report:
            save_atomic(args.report, result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result['ok'] else 1
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f'ORDER_AUDIT_ERROR: {type(exc).__name__}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
