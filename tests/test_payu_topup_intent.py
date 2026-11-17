import pytest
from backend.payu_topup_intent import TopupIntent


def test_topup_intent_uses_integer_grosze():
    intent = TopupIntent("topup-1", 42, 12345)
    assert intent.currency == "PLN"
    assert intent.amount_grosze == 12345


@pytest.mark.parametrize("changes", [
    {"operation_id":""}, {"operation_id":"x"*121}, {"user_id":True},
    {"user_id":0}, {"amount_grosze":0}, {"amount_grosze":100.0},
    {"amount_grosze":True}, {"currency":"EUR"},
])
def test_topup_intent_rejects_invalid_data(changes):
    kwargs = dict(operation_id="topup-1",user_id=42,amount_grosze=100)
    kwargs.update(changes)
    with pytest.raises(ValueError):
        TopupIntent(**kwargs)
