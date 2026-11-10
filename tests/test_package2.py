from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_role_panels_and_notifications():
    html=(ROOT/'web/index.html').read_text()
    js=(ROOT/'web/dashboard.js').read_text()
    for role in ('klient','rolnik','dostawca','admin'):
        assert f"role==='{role}'" in js
    for path in ('/couriers/me/orders','/notifications/me','/orders/me','/orders/${id}/events'):
        assert path in js
    assert 'dashboard.js' in html and 'notifications-section' in html
def test_safe_dom_rendering_and_no_persistent_token():
    js=(ROOT/'web/dashboard.js').read_text()
    assert 'innerHTML' not in js and 'localStorage' not in js
    assert 'node(' in js
