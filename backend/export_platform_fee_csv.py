"""Export a non-fiscal monthly platform-fee CSV from an existing SQLite database.

Usage:
    python -m backend.export_platform_fee_csv /path/to/database.sqlite 2026 11 > fees.csv

Read-only: does not initialize schemas, write to the database or issue invoices.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

from backend.platform_fee_ledger import monthly_platform_fee_csv


def export_csv(database_path: str, year: int, month: int) -> str:
    path = Path(database_path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError("Database path must point to an existing file")
    # SQLite URI mode=ro prevents accidental writes and creation of new databases.
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as con:
        return monthly_platform_fee_csv(con, year, month)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Export internal monthly platform fees (CSV, not a fiscal invoice)"
    )
    parser.add_argument("database", help="Path to existing SQLite database")
    parser.add_argument("year", type=int)
    parser.add_argument("month", type=int)
    args = parser.parse_args(argv)
    try:
        csv_text = export_csv(args.database, args.year, args.month)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(csv_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
