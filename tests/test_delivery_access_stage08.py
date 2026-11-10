from backend.delivery_access import courier_may_see_address


def access(**changes):
    kwargs = dict(actor_id=7, courier_id=7, fulfillment='dostawa',
                  status='w_drodze_testowo', pin_used=0, confirmed_at=None)
    kwargs.update(changes)
    return courier_may_see_address(**kwargs)


def test_only_assigned_courier_during_dispatch():
    assert access()
    assert not access(courier_id=8)
    assert not access(courier_id=None)
    assert not access(actor_id='7')


def test_address_hidden_before_dispatch_and_after_pin():
    assert not access(status='oczekuje_na_platnosc_testowa')
    assert not access(status='odebrane')
    assert not access(pin_used=1)
    assert not access(confirmed_at='2026-10-14T10:00:00Z')
    assert not access(fulfillment='odbior')
