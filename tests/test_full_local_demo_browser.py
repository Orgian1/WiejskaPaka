"""All enabled local demo panels in Chromium at phone and desktop sizes."""
from io import BytesIO
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest
from scripts.run_phone_demo import full_demo_environment
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('width', [320, 1280])
def test_public_footer_shared_contact_form(full_demo_server, delivery_browser, width):
    url, _ = full_demo_server
    page = delivery_browser.new_page(viewport={'width': width, 'height': 844})
    writes,queries = [],[]
    def capture(request):
        if request.method!='POST':return
        if request.url.endswith('/catalog/query'):queries.append(request.post_data_json)
        else:writes.append(request.url)
    page.on('request',capture)
    try:
        page.goto(url)
        page.click('#contact-nav-link');page.locator('#footer-contact-toggle').click()
        assert page.locator('#contact-topic').input_value() == 'contact'
        page.locator('#contact-email').fill('guest@example.invalid')
        page.locator('#contact-subject').fill('Pytanie o działanie strony')
        page.locator('#contact-message').fill('Treść wiadomości próbnej')
        page.select_option('#contact-topic','problem')
        assert page.locator('#contact-topic').input_value() == 'problem'
        assert page.locator('#contact-message').input_value() == 'Treść wiadomości próbnej'
        assert page.locator('#contact-disclosure').evaluate('(node)=>node.open')
        assert page.locator('#contact-submit').is_disabled()
        page.locator('#contact-form').evaluate('(form) => form.requestSubmit()')
        assert 'nie została wysłana' in page.locator('#contact-status').inner_text()
        assert not writes
        assert all(set(query)<= {'q','limit','offset','category_id','subcategory_id','available_now','fulfillment','sort','farmer_id','latitude_e6','longitude_e6'} for query in queries)
        assert all('guest@example.invalid' not in json.dumps(query) and 'Treść wiadomości próbnej' not in json.dumps(query,ensure_ascii=False) for query in queries)
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
        with server(Path(sample['database']), reset_outbox=directory/"reset-mailbox") as client:
            yield str(client.base_url),sample['credentials']


def close_login_guide(page):
    page.locator('#login-guide').get_by_role('button').click(timeout=10000)


@pytest.mark.parametrize('role',['klient','rolnik','dostawca','admin'])
@pytest.mark.parametrize('width',[320,1280])
def test_complete_demo_role_panels(full_demo_server,delivery_browser,role,width):
    url,accounts=full_demo_server
    page=delivery_browser.new_page(viewport={'width':width,'height':844})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    try:
        page.goto(url)
        page.click('#account-nav-link');page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
        page.locator('#auth button[type=submit]').click()
        if role in ('klient','rolnik'):
            close_login_guide(page)
        page.click('#panel-nav-link')
        page.locator('#dashboard-content article').first.wait_for(state='visible')
        assert page.locator('#header-login-link').is_hidden()
        assert page.locator('#header-register-link').is_hidden()
        assert page.locator('#header-panel-link').is_visible()
        if role in ('klient','rolnik'):
            page.locator('#dashboard').get_by_text(re.compile(r'^Przesyłka A001-\d{3}$')).first.wait_for()
        if role in ('klient','rolnik'):
            page.click('#wallet-nav-link');page.locator('#wallet-section').wait_for(state='visible')
        else:
            assert page.locator('#wallet-nav-link').count()==0 or page.locator('#wallet-nav-link').is_hidden()
        if role=='rolnik':
            shortcut = page.get_by_role('button', name='Kod rabatowy: START3-DEMO', exact=True)
            shortcut.wait_for()
            assert page.locator('#seller-point-nav').bounding_box()['width'] < 220
            shortcut.click()
            assert page.locator('#pickup-promo-code').input_value() == 'START3-DEMO'
            page.click('#orders-nav-link')
            page.locator('#address-delivery-panel').wait_for(state='visible')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.click('#logout')
        page.locator('#auth').wait_for(state='visible')
        assert page.locator('#header-login-link').is_visible()
        assert page.locator('#header-register-link').is_visible()
        assert page.locator('#header-panel-link').is_hidden()
        assert not errors
    finally:page.close()


def test_new_seller_guide_and_first_listing_promotion(full_demo_server, delivery_browser):
    from PIL import Image
    from playwright.sync_api import expect

    url, _ = full_demo_server
    context = delivery_browser.new_context(
        viewport={'width': 390, 'height': 844},
        permissions=['clipboard-read', 'clipboard-write'],
    )
    page = context.new_page()
    account = {'email': 'first-offer@example.invalid', 'password': 'Test-First-Offer-987!'}
    try:
        page.goto(url)
        page.click('#header-register-link')
        page.fill('#email', account['email'])
        page.fill('#password', account['password'])
        page.select_option('#role', 'rolnik')
        with page.expect_response('**/auth/register') as registered:
            page.click('#register')
        assert registered.value.status == 201
        expect(page.locator('#notice')).to_contain_text('Teraz się zaloguj.')
        expect(page.locator('#auth')).to_be_visible()

        page.fill('#password', account['password'])
        page.locator('#auth button[type=submit]').click()
        guide = page.get_by_role('dialog', name='Jak zacząć sprzedawać w WiejskiejPace?')
        close_guide = guide.get_by_role('button', name='Zamknij instrukcję sprzedawcy')
        expect(guide).to_be_visible()
        expect(page.locator('#dashboard')).to_be_visible()
        expect(close_guide).to_be_disabled()
        expect(guide.get_by_role('timer')).to_have_text('5')
        expect(close_guide).to_have_css('color', 'rgb(192, 0, 0)')
        assert guide.evaluate('(dialog) => dialog.scrollWidth <= dialog.clientWidth')
        page.keyboard.press('Escape')
        expect(guide).to_be_visible()
        expect(guide.get_by_text('PIN odbioru', exact=False)).to_be_visible()
        expect(close_guide).to_be_enabled(timeout=7000)
        expect(guide).to_be_visible()
        close_guide.click()
        expect(guide).to_be_hidden()

        page.click('#account-nav-link')
        page.click('#logout')
        page.reload()
        page.click('#header-login-link')
        page.fill('#email', account['email'])
        page.fill('#password', account['password'])
        page.locator('#auth button[type=submit]').click()
        close_login_guide(page)
        page.click('#seller-nav-link')
        notice = page.get_by_role('dialog', name='Dodajesz pierwszą ofertę')
        expect(notice.get_by_text('WiejskaPaka pobiera 5%', exact=False)).to_be_visible()
        expect(notice.get_by_text('pierwsze 3 punkty odbioru są darmowe przez 30 dni', exact=False)).to_be_visible()
        notice.get_by_role('button', name='Kopiuj kod').click()
        expect(notice.get_by_role('status')).to_have_text('Kod skopiowany.')
        assert page.evaluate('navigator.clipboard.readText()') == 'START3-DEMO'
        notice.get_by_role('button', name='Przejdź do realizacji kodu').click()
        assert page.locator('#pickup-promo-code').input_value() == 'START3-DEMO'
        with page.expect_response('**/pickup-promotions/redeem') as redeemed:
            page.click('#pickup-promo-redeem-submit')
        assert redeemed.value.status == 201
        assert redeemed.value.json()['remaining'] == 3
        for number in range(3):
            point = page.evaluate("""index => api('/pickup-points', 'POST', {
                name: 'Nowy punkt ' + index, city: 'Legnica', street: 'Testowa 1',
                opening_hours: '9–16'
            })""", number)
            assert point['promotion']
        page.click('#panel-nav-link')
        page.click('#points-nav-link')
        seventh = page.get_by_role('button', name='Siódmy punkt gratis na 30 dni: PUNKT7-DEMO')
        expect(seventh).to_be_visible()
        seventh.click()
        assert page.locator('#pickup-promo-code').input_value() == 'PUNKT7-DEMO'
        page.click('#seller-nav-link')
        assert notice.is_hidden()
        page.select_option('#product-category', 'vegetables')
        page.select_option('#product-subcategory', 'vegetables-tomatoes')
        page.fill('#pname', 'Pierwsze pomidory')
        page.fill('#price', '3,99')
        page.fill('#delivery', '0')
        page.fill('#stock', '4')
        photo = BytesIO()
        Image.new('RGB', (320, 240), 'red').save(photo, format='JPEG')
        page.set_input_files('#product-photo-file', {
            'name': 'pomidory.jpg', 'mimeType': 'image/jpeg', 'buffer': photo.getvalue(),
        })
        with page.expect_response('**/products/with-photo') as created:
            page.locator('#new-product').get_by_role('button', name='Dodaj produkt', exact=True).click()
        assert created.value.status == 201
        page.click('#account-nav-link')
        page.click('#logout')
        page.fill('#email', account['email'])
        page.fill('#password', account['password'])
        page.locator('#auth button[type=submit]').click()
        close_login_guide(page)
        page.click('#seller-nav-link')
        page.get_by_role('heading', name='Pierwsze pomidory').wait_for()
        assert notice.is_hidden()
    finally:
        context.close()

@pytest.mark.parametrize(('role','title','content'), [
    ('klient', 'Jak kupować w WiejskiejPace?', 'Serduszkiem zapiszesz produkt'),
    ('rolnik', 'Jak zacząć sprzedawać w WiejskiejPace?', '5% od każdej wypłaty'),
])
def test_instructions_for_the_first_five_logins(full_demo_server, delivery_browser, role, title, content):
    from playwright.sync_api import expect

    url, accounts = full_demo_server
    page = delivery_browser.new_page(viewport={'width': 375, 'height': 812})
    page.clock.install()
    guide = page.get_by_role('dialog', name=title)
    try:
        page.goto(url)
        page.click('#header-login-link')
        page.fill('#email', accounts[role]['email'])
        page.fill('#password', 'Niepoprawne-haslo-123!')
        with page.expect_response('**/auth/login') as rejected:
            page.locator('#auth button[type=submit]').click()
        assert rejected.value.status == 401
        expect(guide).to_be_hidden()

        for number in range(1, 7):
            if number == 4:
                page.reload()
                page.click('#header-login-link')
            page.fill('#email', accounts[role]['email'])
            page.fill('#password', accounts[role]['password'])
            page.locator('#auth button[type=submit]').click()
            expect(page.locator('#auth')).to_be_hidden()
            if number <= 5:
                expect(guide.get_by_text(content, exact=False)).to_be_visible()
                expect(guide.get_by_role('button')).to_be_disabled()
                page.clock.fast_forward(5000)
                expect(guide).to_be_visible()
                close_login_guide(page)
            expect(page.locator('#login-guide')).to_be_hidden()
            page.click('#account-nav-link')
            with page.expect_response('**/auth/logout') as logged_out:
                page.click('#logout')
            assert logged_out.value.status == 200
    finally:
        page.close()
