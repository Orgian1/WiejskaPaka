"""Enabled delivery UI over real localhost HTTP, with disposable SQLite only."""
import shutil
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4

import pytest

from tests.test_purchase_record_http_restart import server


@pytest.fixture(scope='module')
def delivery_browser():
    binary = next((shutil.which(n) for n in ('chromium', 'chromium-browser', 'google-chrome')
                   if shutil.which(n)), None)
    if not binary:
        pytest.skip('Local Chromium required')
    driver_module = pytest.importorskip('playwright.sync_api')
    with driver_module.sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, executable_path=binary,
                                        args=['--no-sandbox', '--no-proxy-server', '--proxy-bypass-list=*'])
        try:
            yield browser
        finally:
            browser.close()


def login(page, url, account):
    page.goto(url)
    page.fill('#email', account['email'])
    page.fill('#password', account['password'])
    page.locator('#auth button[type=submit]').click()
    page.wait_for_function('(email)=>document.querySelector("#identity").textContent.includes(email)',
                           arg=account['email'])
    page.locator('#address-delivery-panel').wait_for(state='visible')


@pytest.mark.parametrize('width', [320, 1280])
@pytest.mark.parametrize('decision', ['accepted', 'declined'])
def test_delivery_window_checkout_and_seller_decision(delivery_browser, tmp_path, monkeypatch, width, decision):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_DELIVERY', '1')
    day = datetime.now(ZoneInfo('Europe/Warsaw')).date() + timedelta(days=7)
    with server(tmp_path/'delivery.sqlite3') as client:
        accounts = []
        headers = []
        for role in ('rolnik', 'klient'):
            account = {'email': uuid4().hex+'@example.invalid',
                       'password': 'SyntheticPrivate2026', 'role': role}
            response = client.post('/auth/register', json=account)
            assert response.status_code == 201, response.text
            token = client.post('/auth/login', json=account).json()['access_token']
            accounts.append(account)
            headers.append({'Authorization': 'Bearer '+token})
        product = client.post('/products', headers=headers[0], json={
            'name': 'Pomidory przeglądarkowe', 'stock': 10, 'price_grosze': 200, 'delivery_grosze': 500})
        assert product.status_code == 201, product.text
        seller = delivery_browser.new_page(viewport={'width': width, 'height': 844})
        buyer = delivery_browser.new_page(viewport={'width': width, 'height': 844})
        errors = []
        for page in (seller, buyer):
            page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            login(seller, str(client.base_url), accounts[0])
            seller.click('#delivery-settings-tab')
            seller.fill('#delivery-window-city', 'Legnica')
            seller.fill('#delivery-window-postal', '59-220')
            seller.select_option('#delivery-window-day', str(day.weekday()))
            seller.fill('#delivery-window-from', '10:00')
            seller.fill('#delivery-window-to', '16:00')
            with seller.expect_response('**/address-delivery/windows') as response:
                seller.click('#delivery-window-save')
            assert response.value.status == 200
            seller.locator('#delivery-window-list article').wait_for(state='visible')
            assert seller.evaluate('document.documentElement.scrollWidth <= innerWidth')
            login(buyer, str(client.base_url), accounts[1])
            card = buyer.locator('#products > .card').filter(has_text='Pomidory przeglądarkowe')
            card.get_by_label('Sposób realizacji').select_option('dostawa')
            card.get_by_label('Miejscowość dostawy', exact=True).fill('Legnica')
            card.get_by_label('Ulica i numer dostawy', exact=True).fill('Testowa 1')
            card.get_by_label('Kod pocztowy dostawy', exact=True).fill('59-220')
            slot = card.get_by_label('Termin dostawy sprzedawcy', exact=True)
            buyer.wait_for_function('document.querySelector("#products fieldset select").options.length === 2')
            slot.select_option(index=1)
            card.get_by_label('Data dostawy', exact=True).fill(day.isoformat())
            card.get_by_label('Odbiorę w domu od godziny', exact=True).fill('12:00')
            card.get_by_label('Odbiorę w domu do godziny', exact=True).fill('18:00')
            card.get_by_label('Prywatny numer telefonu klienta', exact=True).fill('+48 500 100 200')
            assert buyer.evaluate('document.documentElement.scrollWidth <= innerWidth')
            with buyer.expect_response('**/orders') as response:
                card.get_by_role('button', name='Zamów testowo', exact=True).click()
            assert response.value.status == 201
            oid = response.value.json()['id']
            # The seller decides through the actual UI; no mocked requests or DOM.
            seller.click('#delivery-view-refresh')
            request = seller.locator('#delivery-requests article').first
            button = request.get_by_role('button', name='Akceptuję dostawę' if decision == 'accepted' else 'Odrzucam dostawę', exact=True)
            button.wait_for(state='visible')
            with seller.expect_response(f'**/address-delivery/requests/{oid}/decision') as response:
                button.click()
            assert response.value.status == 200
            request.get_by_text('Zaakceptowana' if decision == 'accepted' else 'Odrzucona', exact=False).wait_for(state='visible')
            buyer.click('#delivery-view-refresh')
            buyer.locator('#delivery-requests').get_by_text('Zaakceptowana' if decision == 'accepted' else 'Odrzucona', exact=False).wait_for(state='visible')
            assert buyer.locator('#delivery-requests button').count() == 0
            for page in (seller, buyer):
                assert '500 100 200' not in page.locator('#delivery-requests').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.set_viewport_size({'width': 844, 'height': 390})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.click('#logout')
                page.locator('#address-delivery-panel').wait_for(state='hidden')
                assert page.locator('#delivery-requests').inner_text() == ''
                page.wait_for_function("document.querySelectorAll('input[type=tel]').length === 0")
            assert not errors
        finally:
            seller.close()
            buyer.close()
