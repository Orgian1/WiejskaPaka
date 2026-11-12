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
    sources=[s['src'] for s in doc.scripts]
    assert len(sources)==len(set(sources))
    for src in sources:
        assert src.startswith('/assets/') and (ROOT/'web'/src.removeprefix('/assets/')).is_file()
    for required in ('leaflet','app','dashboard','nearby','pickup-calendar','address-search','address-delivery','user-photos','seller-search','same-package','purchase-records','pin-recovery','account-security','session-security','password-reset','email-verification','seller-compliance','admin-seller-review','support-cases','wallet','contact','favorites','seller-navigation','saved-location','seller-panels','pickup-map','pickup-promotions'):
        assert '/assets/'+required+'.js' in sources
    for dependency,consumer in [('leaflet','pickup-map'),('app','dashboard'),('app','nearby'),('nearby','address-search'),('nearby','pickup-map'),('seller-panels','pickup-map'),('app','favorites')]:
        assert sources.index('/assets/'+dependency+'.js')<sources.index('/assets/'+consumer+'.js')
    assert all('defer' in s for s in doc.scripts)
