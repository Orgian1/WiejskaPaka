"""Regression tests for courier address visibility and endpoint privacy."""
from pathlib import Path
from backend.delivery_access import courier_may_see_address


def test_courier_cannot_see_address_before_dispatch():
    assert not courier_may_see_address(actor_id=5, courier_id=5, fulfillment='dostawa',
        status='oczekuje_na_platnosc_testowa', pin_used=0, confirmed_at=None)

def test_courier_can_see_address_during_delivery():
    assert courier_may_see_address(actor_id=5, courier_id=5, fulfillment='dostawa',
        status='w_drodze_testowo', pin_used=0, confirmed_at=None)

def test_courier_loses_access_after_pin():
    assert not courier_may_see_address(actor_id=5, courier_id=5, fulfillment='dostawa',
        status='w_drodze_testowo', pin_used=1, confirmed_at='2026-10-14')

def test_farmer_endpoint_guard_exists():
    code = (Path(__file__).resolve().parents[1] / 'backend' / 'app.py').read_text()
    assert "user['role']=='rolnik' and row['farmer_id']==user['id']" in code
    assert "and row['fulfillment']=='odbior'" in code
