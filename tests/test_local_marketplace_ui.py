"""Execute the real UI script with Node's DOM/fetch/location harness; no Chromium claim."""
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case',[
    'coordinate_precision','location_requires_click','public_query_private_body','latest_request_wins',
    'input_invalidates_response','logout_clears_coordinates','reset_aborts_pending_response',
    'stale_cart_button_cannot_write','point_owner_switch_clears_old_result','point_edit_coordinates_atomic',
    'price_range_blocks_fetch','error_and_retry',
])
def test_real_nearby_javascript_behaviour(case):
    run=subprocess.run(['node','scripts/local_marketplace_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=15)
    assert run.returncode==0,run.stdout+run.stderr


def test_nearby_markup_privacy_and_mobile_contract():
    from scripts.audit_mobile_markup import audit_markup
    assert audit_markup()['ok']
    html=(ROOT/'web/index.html').read_text()
    assert 'id="point-location-panel" hidden' in html
    assert '/assets/nearby.js' in html
    assert all(f'value="{r}"' in html for r in (100,500,1000,5000))
    assert 'autocomplete="off"' in html


def test_scripts_load_after_document_in_dependency_order():
    from html.parser import HTMLParser
    class Scripts(HTMLParser):
        def __init__(self):
            super().__init__();self.scripts=[]
        def handle_starttag(self,tag,attrs):
            if tag=='script':self.scripts.append(dict(attrs))
    doc=Scripts();doc.feed((ROOT/'web/index.html').read_text())
    assert [s['src'] for s in doc.scripts]==['/assets/app.js','/assets/dashboard.js','/assets/nearby.js','/assets/address-search.js','/assets/purchase-records.js','/assets/pin-recovery.js','/assets/account-security.js','/assets/session-security.js','/assets/password-reset.js','/assets/seller-compliance.js','/assets/admin-seller-review.js','/assets/support-cases.js']
    assert all('defer' in s for s in doc.scripts)
