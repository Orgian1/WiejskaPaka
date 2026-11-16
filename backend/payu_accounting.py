"""Strict accounting invariant helpers for a future provider ledger.

These calculations are pure and do not touch the real wallet or provider.
"""


def assert_refund_budget(original_grosze: int, completed_refunds_grosze: int,
                         requested_refund_grosze: int) -> int:
    for value in (original_grosze, completed_refunds_grosze, requested_refund_grosze):
        if type(value) is not int:
            raise ValueError("Money must be integer grosze")
    if original_grosze <= 0 or completed_refunds_grosze < 0 or requested_refund_grosze <= 0:
        raise ValueError("Invalid refund amounts")
    if completed_refunds_grosze > original_grosze:
        raise ValueError("Existing refunds exceed original amount")
    if completed_refunds_grosze + requested_refund_grosze > original_grosze:
        raise ValueError("Refund exceeds remaining amount")
    return original_grosze - completed_refunds_grosze - requested_refund_grosze


def assert_balanced_postings(entries_grosze: list[int]) -> None:
    if not entries_grosze or any(type(v) is not int for v in entries_grosze):
        raise ValueError("Journal entries must be integer grosze")
    if sum(entries_grosze) != 0:
        raise ValueError("Unbalanced financial journal")
