"""Reconciliation helpers for verified provider records.

This module is deliberately pure: it never makes financial postings, initiates
payouts, or trusts a browser redirect as proof of payment.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderBalance:
    operation_id: str
    expected_grosze: int
    confirmed_grosze: int

    def __post_init__(self):
        if not self.operation_id:
            raise ValueError("Missing operation identifier")
        for value in (self.expected_grosze, self.confirmed_grosze):
            if type(value) is not int or value < 0:
                raise ValueError("Reconciliation amounts must be nonnegative integer grosze")

    @property
    def difference_grosze(self) -> int:
        return self.confirmed_grosze - self.expected_grosze


def reconciliation_mismatches(rows: list[ProviderBalance]) -> list[ProviderBalance]:
    seen = set()
    mismatches = []
    for row in rows:
        if row.operation_id in seen:
            raise ValueError("Duplicate operation in provider reconciliation")
        seen.add(row.operation_id)
        if row.difference_grosze:
            mismatches.append(row)
    return mismatches
