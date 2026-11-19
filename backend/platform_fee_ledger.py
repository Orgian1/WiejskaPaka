"""Isolated, non-fiscal platform fee ledger schema and read-only posting helpers.

No payment provider calls, invoice issuance or production activation.
"""
import sqlite3
from datetime import date

ALLOWED_KINDS = frozenset(("pickup_point", "seller_withdrawal_fee", "advertising"))


def initialize_platform_fee_ledger(con: sqlite3.Connection) -> None:
    """Create an isolated ledger table; does not import or migrate wallet balances."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS platform_fee_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL UNIQUE CHECK (length(trim(source_id)) > 0),
            seller_id INTEGER NOT NULL CHECK (seller_id > 0),
            posted_on TEXT NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('pickup_point','seller_withdrawal_fee','advertising')),
            amount_grosze INTEGER NOT NULL CHECK (typeof(amount_grosze) = 'integer'),
            currency TEXT NOT NULL DEFAULT 'PLN' CHECK (currency = 'PLN'),
            correction_of TEXT,
            provider_reference TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (correction_of) REFERENCES platform_fee_ledger(source_id),
            CHECK (correction_of IS NULL OR correction_of != source_id)
        )
    """)


    con.execute("""
        CREATE TRIGGER IF NOT EXISTS platform_fee_ledger_validate_insert
        BEFORE INSERT ON platform_fee_ledger
        BEGIN
            SELECT CASE WHEN NEW.posted_on IS NULL OR length(NEW.posted_on) != 10
                OR NEW.posted_on NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                OR date(NEW.posted_on, '+0 days') IS NULL
                OR date(NEW.posted_on, '+0 days') != NEW.posted_on
                THEN RAISE(ABORT, 'Invalid ledger posting date') END;
            SELECT CASE WHEN NEW.correction_of IS NULL AND NEW.amount_grosze <= 0
                THEN RAISE(ABORT, 'New fee must be positive') END;
            SELECT CASE WHEN NEW.correction_of IS NOT NULL AND NEW.amount_grosze >= 0
                THEN RAISE(ABORT, 'Correction must be negative') END;
            SELECT CASE WHEN NEW.correction_of IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM platform_fee_ledger orig
                WHERE orig.source_id = NEW.correction_of
                  AND orig.correction_of IS NULL
                  AND orig.seller_id = NEW.seller_id
                  AND orig.kind = NEW.kind AND orig.currency = NEW.currency
            ) THEN RAISE(ABORT, 'Correction must match original fee') END;
            SELECT CASE WHEN NEW.correction_of IS NOT NULL AND (
                SELECT COALESCE(SUM(amount_grosze), 0)
                FROM platform_fee_ledger
                WHERE correction_of = NEW.correction_of
            ) + NEW.amount_grosze < -(
                SELECT amount_grosze FROM platform_fee_ledger
                WHERE source_id = NEW.correction_of
            ) THEN RAISE(ABORT, 'Corrections exceed original fee') END;
        END
    """)
    con.execute("""
        CREATE TRIGGER IF NOT EXISTS platform_fee_ledger_no_update
        BEFORE UPDATE ON platform_fee_ledger
        BEGIN
            SELECT RAISE(ABORT, 'Platform fee ledger entries are immutable');
        END
    """)
    con.execute("""
        CREATE TRIGGER IF NOT EXISTS platform_fee_ledger_no_delete
        BEFORE DELETE ON platform_fee_ledger
        BEGIN
            SELECT RAISE(ABORT, 'Platform fee ledger entries are immutable');
        END
    """)


def add_platform_fee_entry(con: sqlite3.Connection, *, source_id: str,
                           seller_id: int, posted_on: str, kind: str,
                           amount_grosze: int, correction_of: str | None = None,
                           provider_reference: str | None = None) -> None:
    """Insert exactly one traceable fee event. Caller controls transaction commit.

    This records a fee claim, not confirmation of payment or tax liability.
    """
    if type(source_id) is not str or not source_id.strip():
        raise ValueError("Invalid source ID")
    if type(seller_id) is not int or seller_id < 1:
        raise ValueError("Invalid seller ID")
    if type(posted_on) is not str or len(posted_on) != 10:
        raise ValueError("Invalid posting date")
    try:
        if date.fromisoformat(posted_on).isoformat() != posted_on:
            raise ValueError("Invalid posting date")
    except ValueError as exc:
        raise ValueError("Invalid posting date") from exc
    if kind not in ALLOWED_KINDS or type(amount_grosze) is not int or amount_grosze == 0:
        raise ValueError("Invalid fee event")
    if correction_of is not None:
        if type(correction_of) is not str or not correction_of.strip() or correction_of == source_id:
            raise ValueError("Invalid correction reference")
        original = con.execute(
            "SELECT seller_id, kind, currency FROM platform_fee_ledger WHERE source_id = ?",
            (correction_of,),
        ).fetchone()
        if original is None or (original[0], original[1], original[2]) != (seller_id, kind, "PLN"):
            raise ValueError("Correction must refer to matching fee")
    elif amount_grosze < 0:
        raise ValueError("Negative fees require correction reference")
    if correction_of is not None and amount_grosze > 0:
        raise ValueError("Positive adjustments must be recorded as separate fee events")
    if correction_of is not None and amount_grosze < 0:
        original_amount = con.execute(
            "SELECT amount_grosze FROM platform_fee_ledger WHERE source_id = ?",
            (correction_of,),
        ).fetchone()[0]
        if original_amount <= 0:
            raise ValueError("Refund must reference a positive original fee")
        refunded = con.execute(
            "SELECT COALESCE(SUM(amount_grosze), 0) FROM platform_fee_ledger "
            "WHERE correction_of = ? AND amount_grosze < 0",
            (correction_of,),
        ).fetchone()[0]
        if refunded + amount_grosze < -original_amount:
            raise ValueError("Corrections exceed original fee")
    if provider_reference is not None and (type(provider_reference) is not str or not provider_reference.strip()):
        raise ValueError("Invalid provider reference")
    con.execute("""
        INSERT INTO platform_fee_ledger
            (source_id, seller_id, posted_on, kind, amount_grosze, correction_of, provider_reference)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (source_id, seller_id, posted_on, kind, amount_grosze, correction_of, provider_reference))


def monthly_platform_fee_entries(con: sqlite3.Connection, year: int, month: int) -> list[dict]:
    """Read a month of ledger entries for the existing audit/reporting pipeline."""
    if type(year) is not int or type(month) is not int:
        raise ValueError("Invalid reporting period")
    try:
        date(year, month, 1)
        if year == 9999 and month == 12:
            raise ValueError("Invalid reporting period")
    except ValueError as exc:
        raise ValueError("Invalid reporting period") from exc
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year + 1:04d}-01-01" if month == 12 else f"{year:04d}-{month + 1:02d}-01"
    rows = con.execute("""
        SELECT source_id, seller_id, posted_on, kind, amount_grosze, currency
        FROM platform_fee_ledger WHERE posted_on >= ? AND posted_on < ?
        ORDER BY posted_on, id
    """, (start, end)).fetchall()
    return [dict(zip(("source_id", "seller_id", "posted_on", "kind", "amount_grosze", "currency"), row))
            for row in rows]


def monthly_platform_fee_draft(con: sqlite3.Connection, year: int, month: int) -> dict:
    """Internal draft only; ledger events are not evidence of PSP settlement."""
    from backend.monthly_platform_fees import monthly_fee_draft_payload

    entries = monthly_platform_fee_entries(con, year, month)
    draft = monthly_fee_draft_payload(entries, year, month)
    draft["source_system"] = "platform_fee_ledger"
    draft["payment_provider_confirmed"] = False
    draft["fiscal_document"] = False
    return draft
