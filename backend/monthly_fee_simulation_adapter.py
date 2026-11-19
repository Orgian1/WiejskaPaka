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
               r.created_at AS resolved_at, r.withdrawal_id AS withdrawal_id,
               t.fee_grosze AS amount_grosze,
               t.gross_grosze AS gross_grosze, t.net_grosze AS net_grosze,
               e.user_id AS entry_user_id, e.kind AS entry_kind,
               t.owner_role AS owner_role, t.fee_basis_points AS fee_basis_points
        FROM wallet_preview_resolutions r
        LEFT JOIN wallet_preview_terms t ON t.withdrawal_id = r.withdrawal_id
        LEFT JOIN wallet_preview_entries e ON e.id = r.withdrawal_id
        WHERE r.state = 'completed_test'
        ORDER BY r.created_at, r.id
    """).fetchall()
    result = []
    seen_resolutions = set()
    seen_withdrawals = set()
    for row in rows:
        stamp = row["resolved_at"]
        if type(stamp) is not int or stamp < 0:
            raise ValueError("Invalid simulation timestamp")
        try:
            posted_on = datetime.fromtimestamp(stamp, tz=timezone.utc).date()
        except (OverflowError, OSError, ValueError) as exc:
            raise ValueError("Invalid simulation timestamp") from exc
        if (posted_on.year, posted_on.month) != (year, month):
            continue
        resolution_id = row["resolution_id"]
        if type(resolution_id) is not str or not resolution_id.strip():
            raise ValueError("Missing simulated resolution ID")
        if resolution_id in seen_resolutions:
            raise ValueError("Duplicate simulated resolution ID")
        seen_resolutions.add(resolution_id)
        withdrawal_id = row["withdrawal_id"]
        if type(withdrawal_id) is not str or not withdrawal_id.strip():
            raise ValueError("Missing simulated withdrawal ID")
        if withdrawal_id in seen_withdrawals:
            raise ValueError("Duplicate simulated withdrawal ID")
        seen_withdrawals.add(withdrawal_id)
        if type(row["seller_id"]) is not int or row["seller_id"] < 1:
            raise ValueError("Invalid simulated withdrawal owner")
        if row["owner_role"] is None or row["entry_kind"] is None:
            raise ValueError("Missing simulated withdrawal source")
        if row["owner_role"] == "klient" and row["fee_basis_points"] == 0:
            if row["entry_kind"] != "withdrawal" or row["entry_user_id"] != row["seller_id"]:
                raise ValueError("Inconsistent simulated customer withdrawal source")
            if (type(row["amount_grosze"]) is not int or row["amount_grosze"] != 0
                    or type(row["gross_grosze"]) is not int
                    or type(row["net_grosze"]) is not int
                    or row["gross_grosze"] < 1
                    or row["net_grosze"] != row["gross_grosze"]):
                raise ValueError("Invalid zero-fee customer withdrawal terms")
            continue
        if row["owner_role"] != "rolnik" or row["fee_basis_points"] != 500 or row["entry_kind"] != "withdrawal":
            raise ValueError("Inconsistent simulated withdrawal source")
        if row["entry_user_id"] != row["seller_id"]:
            raise ValueError("Simulated withdrawal owner mismatch")
        gross = row["gross_grosze"]
        net = row["net_grosze"]
        amount = row["amount_grosze"]
        if type(gross) is not int or type(net) is not int or gross < 1 or net < 0:
            raise ValueError("Invalid simulated withdrawal terms")
        if type(amount) is not int or amount < 0:
            raise ValueError("Invalid simulated withdrawal fee")
        if (gross * 500 + 5000) // 10000 != amount or net + amount != gross:
            raise ValueError("Simulated withdrawal fee mismatch")
        if amount == 0:
            continue
        result.append({
            "seller_id": row["seller_id"],
            "posted_on": posted_on.isoformat(),
            "kind": "seller_withdrawal_fee",
            "amount_grosze": amount,
            "currency": "PLN",
            "source_id": "simulation:withdrawal_resolution:" + str(row["resolution_id"]),
        })
    return result


def simulated_monthly_withdrawal_report(con, year: int, month: int) -> dict:
    """Generate an explicitly test-only audit snapshot, never a fiscal record."""
    from backend.monthly_platform_fees import monthly_fee_audit
    entries = simulated_withdrawal_fee_entries(con, year, month)
    report = monthly_fee_audit(entries, year, month)
    return {
        "schema_version": 1,
        "environment": "simulation_only",
        "fiscal_document": False,
        "bank_transfer_executed": False,
        "report": report,
    }


def simulated_monthly_fee_report(con, year: int, month: int) -> dict:
    """Non-fiscal report with an explicit simulation marker, never a tax invoice."""
    from backend.monthly_platform_fees import monthly_fee_audit
    entries = simulated_withdrawal_fee_entries(con, year, month)
    report = monthly_fee_audit(entries, year, month)
    report["environment"] = "simulation_only"
    report["fiscal_document"] = False
    report["payment_provider_confirmed"] = False
    return report
