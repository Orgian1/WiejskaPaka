"""All enabled local demo panels in Chromium at phone and desktop sizes."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest
from scripts.run_phone_demo import full_demo_environment
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('width', [320,1280])
def test_nearby_location_favorites_and_restore_after_login(full_demo_server, delivery_browser, width):
    url,accounts=full_demo_server
    context=delivery_browser.new_context(viewport={'width':width,'height':844},
        geolocation={'latitude':51.210000,'longitude':16.160000},permissions=['geolocation'])
    page=context.new_page()
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    def login():
        page.fill('#email',accounts['klient']['email']);page.fill('#password',accounts['klient']['password'])
        page.locator('#auth button[type=submit]').click()
        page.locator('#logout').wait_for(state='visible')
    try:
        page.goto(url);login()
        with page.expect_response('**/marketplace/nearby') as found:
            page.click('#nearby-geolocate')
        assert found.value.status==200
        page.locator('#nearby-results article').first.wait_for()
        heart=page.locator('#nearby-results .favorite-button').first
        heart.click();assert heart.get_attribute('aria-pressed')=='true'
        page.click('#favorites-nav-link')
        page.locator('#favorites-list article').first.wait_for()
        assert page.locator('#favorites-list .favorite-button').first.get_attribute('aria-pressed')=='true'
        page.reload();login()
        with page.expect_response('**/marketplace/nearby') as restored:
            page.click('#nearby-nav-link')
        assert restored.value.status==200
        assert page.locator('#nearby-lat').input_value()=='51,210000'
        page.click('#favorites-nav-link');page.locator('#favorites-list article').first.wait_for()
        page.locator('#favorites-list .favorite-button').first.click()
        page.wait_for_function("() => document.querySelector('#favorites-list').children.length===0")
        page.click('#nearby-clear')
        assert page.locator('#nearby-lat').input_value()==''
        page.click('#logout')
        assert page.locator('#nearby-lon').input_value()==''
        assert page.locator('#favorites-list').inner_text()==''
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors
    finally:context.close()


@pytest.mark.parametrize('width',[320,1280])
def test_delivery_counterproposal_seller_and_buyer_ui(full_demo_server,delivery_browser,width):
    import httpx
    from datetime import datetime,timedelta
    from zoneinfo import ZoneInfo
    url,accounts=full_demo_server
    with httpx.Client(base_url=url,trust_env=False) as client:
        def auth(role):
            return {'Authorization':'Bearer '+client.post('/auth/login',json=accounts[role]).json()['access_token']}
        farmer,buyer=auth('rolnik'),auth('klient')
        day=datetime.now(ZoneInfo('Europe/Warsaw')).date()+timedelta(days=7)
        window=client.post('/address-delivery/windows',headers=farmer,json={'city':'Legnica','postal_code':'59-220','weekday':day.weekday(),'from_time':'10:00','to_time':'16:00'}).json()['id']
        pid=client.post('/products',headers=farmer,json={'name':'Oferta negocjacji terminu','stock':4,'price_grosze':200,'delivery_grosze':500}).json()['id']
        response=client.post('/orders',headers=buyer,json={'product_id':pid,'quantity':1,'fulfillment':'dostawa','delivery_city':'Legnica','delivery_street':'Testowa 11','delivery_postal_code':'59-220','address_delivery':{'window_id':window,'delivery_date':str(day),'available_from':'12:00','available_to':'18:00','phone':'+48500100200'}})
        assert response.status_code==201,response.text
        code=response.json()['pickup_code']
    seller=delivery_browser.new_page(viewport={'width':width,'height':844})
    customer=delivery_browser.new_page(viewport={'width':width,'height':844})
    errors=[]
    try:
        for page,role in [(seller,'rolnik'),(customer,'klient')]:
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url);page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
            page.locator('#auth button[type=submit]').click();page.locator('#address-delivery-panel').wait_for(state='visible')
        card=seller.locator('#delivery-requests article').filter(has_text=code)
        card.get_by_text('Zaproponuj inny termin dostawy',exact=True).click()
        card.get_by_label('Proponowana data dostawy').fill(str(day+timedelta(days=1)))
        card.get_by_label('Proponowana dostawa od godziny').fill('11:00')
        card.get_by_label('Proponowana dostawa do godziny').fill('13:00')
        with seller.expect_response('**/proposals') as sent:card.get_by_role('button',name='Wyślij propozycję terminu').click()
        assert sent.value.status==200
        customer.click('#delivery-view-refresh')
        other=customer.locator('#delivery-requests article').filter(has_text=code)
        with customer.expect_response('**/proposal-decision') as accepted:other.get_by_role('button',name='Przyjmuję nowy termin').click()
        assert accepted.value.status==200
        customer.wait_for_function("(code) => [...document.querySelectorAll('#delivery-requests article')].some(c => c.textContent.includes(code) && c.textContent.includes('Zaakceptowana'))",arg=code)
        assert not errors
    finally:seller.close();customer.close()


@pytest.mark.parametrize('width',[320,1280])
def test_seller_point_uses_address_or_device_and_coordinates_are_advanced(full_demo_server,delivery_browser,width):
    url,accounts=full_demo_server
    context=delivery_browser.new_context(viewport={'width':width,'height':844},
        geolocation={'latitude':51.210000,'longitude':16.160000},permissions=['geolocation'])
    page=context.new_page()
    try:
        page.goto(url);page.fill('#email',accounts['rolnik']['email']);page.fill('#password',accounts['rolnik']['password'])
        page.locator('#auth button[type=submit]').click()
        page.locator('#point-edit-form').wait_for(state='visible')
        assert page.locator('#point-edit-lat').is_hidden()
        page.click('#point-use-location')
        page.wait_for_function("() => document.querySelector('#point-edit-status').textContent.includes('Wybrano miejsce')")
        assert page.locator('#point-edit-lat').input_value()=='51,210000'
        page.click('#point-find-address')
        page.locator('#point-location-results button').first.wait_for()
        page.locator('#point-location-results button').first.click()
        assert page.locator('#point-edit-lon').input_value()=='16,160000'
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    finally:context.close()


@pytest.mark.parametrize('width', [320, 1280])
def test_public_footer_shared_contact_form(full_demo_server, delivery_browser, width):
    url, _ = full_demo_server
    page = delivery_browser.new_page(viewport={'width': width, 'height': 844})
    writes = []
    page.on('request', lambda request: writes.append(request.url) if request.method == 'POST' else None)
    try:
        page.goto(url)
        page.locator('#footer-contact-link').click()
        assert page.locator('#contact-topic').input_value() == 'contact'
        page.locator('#contact-email').fill('guest@example.invalid')
        page.locator('#contact-subject').fill('Pytanie o działanie strony')
        page.locator('#contact-message').fill('Treść wiadomości próbnej')
        page.locator('#footer-report-link').click()
        assert page.locator('#contact-topic').input_value() == 'problem'
        assert page.locator('#contact-message').input_value() == 'Treść wiadomości próbnej'
        assert page.locator('#contact-heading').evaluate('(node) => node === document.activeElement')
        assert page.locator('#contact-submit').is_disabled()
        page.locator('#contact-form').evaluate('(form) => form.requestSubmit()')
        assert 'nie została wysłana' in page.locator('#contact-status').inner_text()
        assert not writes
        assert '?' not in page.url
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#contact-form button[type=reset]').click()
        assert page.locator('#contact-message').input_value() == ''
    finally:
        page.close()


@pytest.fixture(scope='module')
def full_demo_server(tmp_path_factory):
    directory=tmp_path_factory.mktemp('full_demo_browser')/'sample'
    setup=subprocess.run([sys.executable,'-m','scripts.prepare_sample_demo','--full-demo','--directory',str(directory)],
                         cwd=ROOT,capture_output=True,text=True,timeout=120)
    assert setup.returncode==0,'Local sample preparation failed; private output withheld'
    sample=json.loads(setup.stdout)
    with patch.dict(os.environ,full_demo_environment(os.environ,Path(sample['database'])),clear=True):
        with server(Path(sample['database'])) as client:
            yield str(client.base_url),sample['credentials']


@pytest.mark.parametrize('role',['klient','rolnik','dostawca','admin'])
@pytest.mark.parametrize('width',[320,1280])
def test_complete_demo_role_panels(full_demo_server,delivery_browser,role,width):
    url,accounts=full_demo_server
    page=delivery_browser.new_page(viewport={'width':width,'height':844})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    try:
        page.goto(url)
        page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
        page.locator('#auth button[type=submit]').click()
        page.locator('#dashboard-content article').first.wait_for(state='visible')
        assert page.locator('#header-login-link').is_hidden()
        assert page.locator('#header-register-link').is_hidden()
        assert page.locator('#header-panel-link').is_visible()
        if role in ('klient','rolnik'):
            page.locator('#wallet-section').wait_for(state='visible')
        else:
            assert page.locator('#wallet-nav-link').count()==0 or page.locator('#wallet-nav-link').is_hidden()
        if role=='rolnik':page.locator('#address-delivery-panel').wait_for(state='visible')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.click('#logout')
        page.locator('#auth').wait_for(state='visible')
        assert page.locator('#header-login-link').is_visible()
        assert page.locator('#header-register-link').is_visible()
        assert page.locator('#header-panel-link').is_hidden()
        assert not errors
    finally:page.close()
