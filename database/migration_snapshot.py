"""Read-only, privacy-preserving SQLite migration snapshot and drift check.

Hashes include all values but no raw personal data is emitted. Run with writes stopped.
"""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def _canonical(value):
    if isinstance(value, bytes):
        return {'blob_sha256': hashlib.sha256(value).hexdigest(), 'size': len(value)}
    if isinstance(value, float):
        return {'sqlite_real_hex': value.hex()}
    return value


def snapshot(path):
    source = Path(path).resolve()
    if not source.is_file():
        raise ValueError('Baza SQLite nie istnieje')
    con = sqlite3.connect(f'file:{source}?mode=ro', uri=True)
    try:
        con.execute('BEGIN')  # consistent read snapshot during the entire inventory
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
        fk_errors = len(con.execute('PRAGMA foreign_key_check').fetchall())
        if integrity != 'ok' or fk_errors:
            raise ValueError(f'Niespójna baza: integrity={integrity}, foreign_keys={fk_errors}')
        names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        result = {}
        for name in names:
            q = '"' + name.replace('"', '""') + '"'
            columns = [r[1] for r in con.execute(f'PRAGMA table_info({q})')]
            digest = hashlib.sha256()
            count = 0
            # Sorting by all columns gives stable hash independent of insertion order,
            # including tables without a declared primary key.
            order = ', '.join(str(i) for i in range(1, len(columns) + 1))
            cursor = con.execute(f'SELECT * FROM {q} ORDER BY {order}' if columns else f'SELECT * FROM {q}')
            for row in cursor:
                encoded = json.dumps([_canonical(v) for v in row], ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
                digest.update(len(encoded).to_bytes(8, 'big'))
                digest.update(encoded)
                count += 1
            result[name] = {'rows': count, 'columns': columns, 'sha256': digest.hexdigest()}
        con.execute('ROLLBACK')
        return {'format': 'wiejskapaka-sqlite-snapshot-v1', 'tables': result,
                'total_rows': sum(item['rows'] for item in result.values())}
    finally:
        con.close()


def compare(expected, actual):
    if expected.get('format') != 'wiejskapaka-sqlite-snapshot-v1':
        raise ValueError('Nieznany format manifestu')
    names = sorted(set(expected['tables']) | set(actual['tables']))
    changes = [name for name in names if expected['tables'].get(name) != actual['tables'].get(name)]
    return {'unchanged': not changes, 'changed_tables': changes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', required=True)
    parser.add_argument('--save', type=Path, help='Zapisz manifest bez danych osobowych')
    parser.add_argument('--verify', type=Path, help='Porównaj z poprzednim manifestem')
    args = parser.parse_args()
    if args.save and args.verify:
        parser.error('Wybierz --save albo --verify')
    current = snapshot(args.sqlite)
    if args.verify:
        result = compare(json.loads(args.verify.read_text(encoding='utf-8')), current)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result['unchanged']:
            raise SystemExit(2)
    elif args.save:
        args.save.write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Zapisano manifest: {args.save}; tabele: {len(current["tables"])}')
    else:
        print(json.dumps(current, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
