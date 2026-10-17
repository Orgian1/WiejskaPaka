import pytest
from backend.invoicing import calculate_commission_grosze

@pytest.mark.parametrize('base,bp,expected', [(0,500,0),(1,5000,1),(1,4999,0),(9999,500,500),(10000,500,500),(12345,1234,1523)])
def test_commission(base,bp,expected):
    assert calculate_commission_grosze(base,bp)==expected

def test_invalid():
    for amount,rate in [(-1,100),(1,-1),(1,10001),(1.0,100),(True,100),(1,False)]:
        with pytest.raises(ValueError): calculate_commission_grosze(amount,rate)
