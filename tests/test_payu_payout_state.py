import pytest

from backend.payu_preparation import PayoutStatus as S
from backend.payu_payout_state import payout_transition


@pytest.mark.parametrize("before,after", [
    (S.REQUESTED,S.APPROVED),(S.REQUESTED,S.REJECTED),
    (S.APPROVED,S.SENT),(S.SENT,S.SETTLED),(S.SENT,S.FAILED),
])
def test_valid_payout_states(before,after):
    assert payout_transition(before,after)


@pytest.mark.parametrize("before,after", [
    (S.REQUESTED,S.SETTLED),(S.REJECTED,S.APPROVED),
    (S.SETTLED,S.FAILED),(S.FAILED,S.SENT),(S.SENT,S.REQUESTED),
])
def test_invalid_payout_states(before,after):
    with pytest.raises(ValueError):
        payout_transition(before,after)


def test_duplicate_payout_event_is_noop():
    assert payout_transition(S.SETTLED,S.SETTLED) is False
