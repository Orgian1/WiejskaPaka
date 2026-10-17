import pytest
from backend.neon_order_access import buyer_orders, farmer_orders, courier_active_delivery_addresses

class Connection:
    def __init__(self):
        self.sql = None
        self.params = None
    def execute(self, sql, params):
        self.sql, self.params = sql, params
        return self
    def fetchall(self):
        return []

@pytest.mark.parametrize('fn,scope', [
    (buyer_orders, 'buyer_id'),
    (farmer_orders, 'farmer_id'),
    (courier_active_delivery_addresses, 'courier_id'),
])
def test_actor_is_bound_not_interpolated(fn, scope):
    db = Connection()
    assert fn(db, 42) == []
    assert '%s' in db.sql and '42' not in db.sql
    assert db.params[0] == 42
    assert scope in db.sql

@pytest.mark.parametrize('fn', [buyer_orders, farmer_orders, courier_active_delivery_addresses])
@pytest.mark.parametrize('bad', [None, True, -1, 0, '5', 1.5])
def test_untrusted_actor_rejected(fn, bad):
    with pytest.raises(ValueError):
        fn(Connection(), bad)

def test_address_access_requires_assignment_active_delivery_and_unconsumed_pin():
    db = Connection()
    courier_active_delivery_addresses(db, 17)
    assert 'JOIN delivery_assignments' in db.sql
    assert "o.fulfillment = 'dostawa'" in db.sql
    assert 'o.pin_used = 0' in db.sql
    assert 'o.confirmed_at IS NULL' in db.sql
    assert db.params == (17, 'w_drodze_testowo')
    assert 'phone' not in db.sql.lower()
