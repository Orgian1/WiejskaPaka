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
    if type(year) is not int or type(month) is not int:\n        raise ValueError("Year and month must be integers")\n    date(year, month, 1)
    totals = defaultdict(lambda: {"amount_grosze": 0, "transactions": 0})
    seen_sources = set()
    allowed = {"pickup_point", "seller_withdrawal_fee", "advertising"}
    for entry in entries:
        posted_value = entry["posted_on"]\n        if type(posted_value) is not str or len(posted_value) != 10:\n            raise ValueError("Invalid posting date")\n        posted = date.fromisoformat(posted_value)\n        if posted.isoformat() != posted_value:\n            raise ValueError("Posting date must be ISO YYYY-MM-DD")
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
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("year", "month", "seller_id", "currency", "fee_type",
                     "transactions", "amount_grosze"))
    for item in monthly_fee_summary(entries, year, month):
        writer.writerow((item["year"], item["month"], item["seller_id"],
                         item["currency"], item["kind"], item["transactions"],
                         item["amount_grosze"]))
    return buffer.getvalue()
