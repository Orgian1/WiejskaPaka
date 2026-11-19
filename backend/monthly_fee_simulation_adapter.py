"""Read-only adapter from completed *test* withdrawals to simulated fee entries.

Never use this adapter for tax invoices, PSP reconciliation or production money.
"""
from datetime import datetime, timezone


def simulated_withdrawal_fee_entries(con, year: int, month: int) -> list[dict]:
    """Read completed seller withdrawal simulations with immutable fee terms.

    Source IDs come from terminal resolution IDs, not mutable account balances.
    """
    if type(year) is not int or type(month) is not int:
        raise ValueError("Invalid reporting period")
    from datetime import date
    date(year, month, 1)
    rows = con.execute("""
        SELECT r.id AS resolution_id, r.user_id AS seller_id,
               r.created_at AS resolved_at, t.fee_grosze AS amount_grosze
        FROM wallet_preview_resolutions r
        JOIN wallet_preview_terms t ON t.withdrawal_id = r.withdrawal_id
        JOIN wallet_preview_entries e ON e.id = r.withdrawal_id
        WHERE r.state = 'completed_test'
          AND t.owner_role = 'rolnik'
          AND t.fee_basis_points = 500
          AND e.kind = 'withdrawal'
        ORDER BY r.created_at, r.id
    """).fetchall()
    result = []
    for row in rows:
        stamp = row["resolved_at"]
        if type(stamp) is not int:
            raise ValueError("Invalid simulation timestamp")
        posted_on = datetime.fromtimestamp(stamp, tz=timezone.utc).date()
        if (posted_on.year, posted_on.month) != (year, month):
            continue
        amount = row["amount_grosze"]
        if type(amount) is not int or amount < 0:
            raise ValueError("Invalid simulated withdrawal fee")
        result.append({
            "seller_id": row["seller_id"],
            "posted_on": posted_on.isoformat(),
            "kind": "seller_withdrawal_fee",
            "amount_grosze": amount,
            "currency": "PLN",
            "source_id": "simulation:withdrawal_resolution:" + str(row["resolution_id"]),
        })
    return result
