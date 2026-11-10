"""Regression checks for the optional Chromium -> real FastAPI delivery scenarios."""
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_browser_backend_bridge.py'


def test_delivery_bridge_has_courier_privacy_checks():
    source = SCRIPT.read_text(encoding='utf-8')
    assert "B/46 unassigned courier has no address OK" in source
    assert "B/48 only active assigned courier sees delivery address OK" in source
    assert "client.get(location_url, headers=stranger_h).status_code == 403" in source


def test_delivery_bridge_revokes_address_after_pin():
    source = SCRIPT.read_text(encoding='utf-8')
    assert "B/49 courier confirms with PIN; address access revoked OK" in source
    assert "client.get('/couriers/me/active-addresses', headers=courier_h).json() == []" in source


def test_delivery_bridge_checks_full_refund_in_grosze():
    source = SCRIPT.read_text(encoding='utf-8')
    assert "refund.json()['refund_grosze'] == 850" in source
    assert "repeated.json()['refund_grosze'] == 850" in source
