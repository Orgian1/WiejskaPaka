import pytest

from backend.payu_reconciliation import ProviderBalance, reconciliation_mismatches


def test_reconciliation_reports_only_mismatched_grosze():
    records = [ProviderBalance("a", 100, 100), ProviderBalance("b", 101, 100),
               ProviderBalance("c", 200, 205)]
    assert [(x.operation_id, x.difference_grosze)
            for x in reconciliation_mismatches(records)] == [("b", -1), ("c", 5)]


def test_reconciliation_rejects_duplicate_operation():
    with pytest.raises(ValueError):
        reconciliation_mismatches([ProviderBalance("a", 1, 1), ProviderBalance("a", 1, 1)])


@pytest.mark.parametrize("value", [0.5, 1.0, -1, True, "100"])
def test_reconciliation_requires_integer_nonnegative_grosze(value):
    with pytest.raises(ValueError):
        ProviderBalance("a", value, 100)
