import pytest
from fastapi.testclient import TestClient
from backend.marketplace_policy import POLICY, breakdown
from backend.app import app


def test_marketplace_not_seller_and_no_real_invoices():
    response = TestClient(app).get('/marketplace/accounting-policy')
    assert response.status_code == 200
    data = response.json()
    assert data['marketplace_role'] == 'posrednik'
    assert data['product_invoices_issued_by_platform'] is False
    assert data['platform_invoices_issued_automatically'] is False
    assert data['real_payments_enabled'] is False
    assert data['ksef_connected'] is False


def test_breakdown_exact_grosze():
    result = breakdown(9999, 1200, 500)
    assert result.total_paid_grosze == 11199
    assert result.seller_settlement_before_other_fees_grosze == 10699
    assert result.platform_commission_grosze + result.seller_settlement_before_other_fees_grosze == result.total_paid_grosze

@pytest.mark.parametrize('amounts', [(-1,0,0),(100,0,101),(1.0,0,0),(True,0,0),(1,False,0),(9_000_000_000_000,1,0)])
def test_breakdown_rejects_invalid(amounts):
    with pytest.raises(ValueError):
        breakdown(*amounts)
