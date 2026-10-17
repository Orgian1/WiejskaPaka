import pytest
from backend.order_amount_limits import checked_order_total, MAX_DB_INTEGER

@pytest.mark.parametrize('price,qty,delivery,expected', [
    (1,1,0,(1,1)), (123,3,50,(369,419)),
    (MAX_DB_INTEGER,1,0,(MAX_DB_INTEGER,MAX_DB_INTEGER)),
])
def test_valid(price,qty,delivery,expected):
    assert checked_order_total(price,qty,delivery)==expected

@pytest.mark.parametrize('values', [
    (MAX_DB_INTEGER,2,0), (MAX_DB_INTEGER,1,1),
    (1,MAX_DB_INTEGER+1,0), (1,1,MAX_DB_INTEGER),
    (0,1,0), (1,0,0), (-1,1,0), (True,1,0),
    (1,1,1.0), ('1',1,0),
])
def test_invalid(values):
    with pytest.raises(ValueError):
        checked_order_total(*values)
