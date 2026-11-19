"""Read-only monthly grouping of platform fees, in integer grosze.

This module prepares accounting data; it does not issue VAT invoices, decide
tax-point dates, or submit anything to KSeF. Payment dates, service dates,
refunds and prepayments must be assessed by the invoicing integration.
"""
from collections import defaultdict
from datetime import date
from typing import Iterable, Mapping


def monthly_fee_summary(entries: Iterable[Mapping], year: int, month: int) -> list[dict]:
    """Group posted platform fees by seller, currency and fee type.

    Required entry fields: seller_id, posted_on (ISO YYYY-MM-DD), kind,
    amount_grosze, currency. Refunds/adjustments are signed entries.
    Rows for other months are ignored. Does not aggregate sales proceeds,
    wallet top-ups, or third-party delivery charges.
    """
    if type(year) is not int or type(month) is not int:
        raise ValueError("Year and month must be integers")
    date(year, month, 1)
    totals = defaultdict(lambda: {"amount_grosze": 0, "transactions": 0})
    seen_sources = set()
    allowed = {"pickup_point", "seller_withdrawal_fee", "advertising"}
    for entry in entries:
        posted_value = entry["posted_on"]
        if type(posted_value) is not str or len(posted_value) != 10:
            raise ValueError("Invalid posting date")
        posted = date.fromisoformat(posted_value)
        if posted.isoformat() != posted_value:
            raise ValueError("Posting date must be ISO YYYY-MM-DD")
        amount = entry["amount_grosze"]
        seller_id = entry["seller_id"]
        kind = entry["kind"]
        currency = entry["currency"]
        if type(amount) is not int:
            raise ValueError("Amounts must be integer grosze")
        if not isinstance(seller_id, int) or isinstance(seller_id, bool) or seller_id <= 0:
            raise ValueError("Invalid seller identifier")
        if kind not in allowed or currency != "PLN":
            raise ValueError("Unsupported platform fee or currency")
        if (posted.year, posted.month) != (year, month):
            continue
        # The source reference identifies one immutable ledger entry. Repeated
        # exports or duplicate joins must not silently double-charge a seller.
        source_id = entry.get("source_id")
        if source_id is not None:
            if not isinstance(source_id, str) or not source_id.strip():
                raise ValueError("Invalid source identifier")
            if source_id in seen_sources:
                raise ValueError("Duplicate accounting source identifier")
            seen_sources.add(source_id)
        item = totals[(seller_id, currency, kind)]
        item["amount_grosze"] += amount
        item["transactions"] += 1
    return [
        {"seller_id": seller_id, "currency": currency, "kind": kind,
         "amount_grosze": value["amount_grosze"],
         "transactions": value["transactions"], "year": year, "month": month}
        for (seller_id, currency, kind), value in sorted(totals.items())
    ]


def monthly_fee_csv(entries: Iterable[Mapping], year: int, month: int) -> str:
    """Export a UTF-8-compatible, accountant-friendly CSV; no personal data.

    Amounts stay in grosze to avoid floating-point and locale ambiguity.
    The output is a *summary*, never an invoice or KSeF submission.
    """
    import csv
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator=chr(10))
    writer.writerow(("year", "month", "seller_id", "currency", "fee_type",
                     "transactions", "amount_grosze"))
    for item in monthly_fee_summary(entries, year, month):
        writer.writerow((item["year"], item["month"], item["seller_id"],
                         item["currency"], item["kind"], item["transactions"],
                         item["amount_grosze"]))
    return buffer.getvalue()


def monthly_fee_reconciliation(entries: Iterable[Mapping], year: int, month: int) -> dict:
    """Produce a read-only control total before any future invoicing.

    All entries are materialized once so the report and control total use
    exactly the same input snapshot. No payment or invoice is created.
    """
    snapshot = list(entries)
    rows = monthly_fee_summary(snapshot, year, month)
    by_currency = {}
    for row in rows:
        currency = row["currency"]
        total = by_currency.setdefault(currency, {"amount_grosze": 0, "transactions": 0})
        total["amount_grosze"] += row["amount_grosze"]
        total["transactions"] += row["transactions"]
    return {
        "year": year,
        "month": month,
        "rows": rows,
        "totals": by_currency,
        "status": "draft_unverified",
    }


def invoice_export_guard(reconciliation: Mapping) -> None:
    """Fail closed: draft summaries must never be sent to invoice providers.

    The actual invoicing integration must independently verify source ledger,
    tax obligations, buyer identity and document requirements. This function
    deliberately does not authorize production invoicing.
    """
    if reconciliation.get("status") != "verified_for_invoicing":
        raise ValueError("Monthly report is not verified for invoicing")
    raise NotImplementedError(
        "Production invoicing is disabled until an approved tax and KSeF integration exists"
    )


def monthly_fee_draft_payload(entries: Iterable[Mapping], year: int, month: int) -> dict:
    """Build a non-fiscal machine-readable report for later reconciliation.

    Explicitly excludes buyer identity, VAT rate, invoice numbers, tax-point
    decisions and all instructions to issue or deliver tax documents.
    """
    report = monthly_fee_reconciliation(entries, year, month)
    return {
        "schema_version": 1,
        "document_type": "internal_monthly_fee_draft",
        "status": report["status"],
        "period": {"year": year, "month": month},
        "rows": report["rows"],
        "control_totals": report["totals"],
        "fiscal_document": False,
    }


def monthly_fee_audit(entries: Iterable[Mapping], year: int, month: int) -> dict:
    """Require traceable source IDs before preparing an accounting audit report.

    Legacy reports may accept entries without source_id for compatibility.
    This stricter path rejects untraceable data and repeated references.
    """
    snapshot = list(entries)
    for entry in snapshot:
        source_id = entry.get("source_id")
        if type(source_id) is not str or not source_id.strip():
            raise ValueError("Accounting audit requires a nonempty source_id")
    report = monthly_fee_reconciliation(snapshot, year, month)
    report["source_count"] = sum(
        1 for entry in snapshot
        if date.fromisoformat(entry["posted_on"]).year == year
        and date.fromisoformat(entry["posted_on"]).month == month
    )
    report["traceable"] = True
    return report
