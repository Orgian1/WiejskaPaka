import pytest

from backend.payu_accounting import assert_refund_budget, assert_balanced_postings


def test_partial_refunds_use_exact_grosze():
    assert assert_refund_budget(1001, 400, 601) == 0


@pytest.mark.parametrize("args", [(100,90,11),(100,101,1),(0,0,1),(100,-1,1),(100,0,True)])
def test_refund_budget_rejects_invalid_amounts(args):
    with pytest.raises(ValueError):
        assert_refund_budget(*args)


def test_balanced_ledger_postings():
    assert_balanced_postings([-1001, 950, 51])


@pytest.mark.parametrize("entries", [[],[100,-99],[True,-1],[1.0,-1]])
def test_reject_unbalanced_or_untyped_postings(entries):
    with pytest.raises(ValueError):
        assert_balanced_postings(entries)
