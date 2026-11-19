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
    date(year, month, 1)
    totals = defaultdict(lambda: {"amount_grosze": 0, "transactions": 0})
    allowed = {"pickup_point", "seller_withdrawal_fee", "advertising"}
    for entry in entries:
        posted = date.fromisoformat(entry["posted_on"])
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
        item = totals[(seller_id, currency, kind)]
        item["amount_grosze"] += amount
        item["transactions"] += 1
    return [
        {"seller_id": seller_id, "currency": currency, "kind": kind,
         "amount_grosze": value["amount_grosze"],
         "transactions": value["transactions"], "year": year, "month": month}
        for (seller_id, currency, kind), value in sorted(totals.items())
    ]
