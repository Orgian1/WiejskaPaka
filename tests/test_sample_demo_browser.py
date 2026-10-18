"""Eight actual Chromium views backed by seeded SQLite and real HTTP, no mock API."""
import shutil
from pathlib import Path
import pytest
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server

@pytest.fixture(scope='module')
def sample_browser_server(tmp_path_factory):
    binary=next((shutil.which(n) for n in ('chromium','chromium-browser','google-chrome') if shutil.which(n)),None)
    if not binary:pytest.skip('Local Chromium required')
    playwright=pytest.importorskip('playwright.sync_api')
    sample=prepare_sample(tmp_path_factory.mktemp('sample_browser')/'sample')
    with server(Path(sample['database'])) as client,playwright.sync_playwright() as driver:
        for credentials in sample['credentials'].values():
            assert client.post('/auth/login',json=credentials).status_code==200
        browser=driver.chromium.launch(headless=True,executable_path=binary,args=['--no-sandbox','--no-proxy-server','--proxy-bypass-list=*'])
        try:yield browser,str(client.base_url),sample['credentials']
        finally:browser.close()


@pytest.mark.parametrize('width',[320,1280])
@pytest.mark.parametrize('role',['klient','rolnik','dostawca','admin'])
def test_seeded_role_page_and_logout_in_chromium(sample_browser_server,width,role):
    browser,url,accounts=sample_browser_server
    page=browser.new_page(viewport={'width':width,'height':844})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    try:
        page.goto(url)
        page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
        with page.expect_response('**/auth/login') as response:
            page.locator('#auth button[type=submit]').click()
        assert response.value.status==200
        assert not errors
        page.wait_for_function('(email)=>document.getElementById("identity").textContent.includes(email)',arg=accounts[role]['email'])
        page.locator('#dashboard-content article').first.wait_for(state='visible')
        assert page.locator('#dashboard-title').text_content()=={'klient':'Panel klienta','rolnik':'Panel rolnika','dostawca':'Panel dostawcy','admin':'Panel administratora'}[role]
        if role=='admin':
            with page.expect_response('**/admin/farmers/compliance-queue?*') as response:
                page.locator('#admin-seller-refresh').focus();page.locator('#admin-seller-refresh').press('Enter')
            assert response.value.status==200 and response.value.json()['total']==1
            page.locator('#admin-seller-results textarea').wait_for(state='visible')
            page.locator('#admin-seller-results textarea').fill('Robocza fikcyjna notatka')
        elif role=='rolnik':
            with page.expect_response('**/farmers/me/compliance') as response:page.click('#seller-compliance-refresh')
            assert response.value.status==200 and response.value.json()['completed_transaction_count']==0
        elif role=='klient':
            assert 'Liczba przesyłek: 2' in page.locator('#dashboard-content').text_content()
        else:
            assert page.locator('#dashboard-content').text_content().count('Przesyłka')>=1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.evaluate('localStorage.length')==0
        page.click('#logout')
        page.wait_for_function("document.getElementById('identity').textContent==='Nie zalogowano'")
        assert page.locator('#dashboard-content').text_content()==''
        assert page.locator('#admin-seller-results').text_content()==''
        assert page.locator('#admin-seller-review').is_hidden()
        assert page.locator('#seller-compliance').is_hidden()
        assert page.locator('#password').input_value()==''
        assert not errors
    finally:page.close()


@pytest.mark.parametrize('width',[320,1280])
def test_full_seeded_receipt_and_review_in_chromium(sample_browser_server,tmp_path,width):
    browser,_,_=sample_browser_server
    sample=prepare_sample(tmp_path/'workflow')
    accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        login=client.post('/auth/login',json=accounts['klient']).json()
        shipments=client.get('/shipments/mine',headers={'Authorization':'Bearer '+login['access_token']}).json()['shipments']
        page=browser.new_page(viewport={'width':width,'height':844})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            page.goto(str(client.base_url))
            def sign_in(role):
                page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
                page.locator('#auth button[type=submit]').click()
                page.wait_for_function('(email)=>document.getElementById("identity").textContent.includes(email)',arg=accounts[role]['email'])
                page.locator('#dashboard-content article').first.wait_for(state='visible')
            def sign_out():
                page.click('#logout')
                page.wait_for_function("document.getElementById('identity').textContent==='Nie zalogowano'")
            def card(sid):
                return page.locator('#dashboard-content > article').filter(has=page.get_by_role('heading',name='Przesyłka '+sid,exact=True))
            pins={}
            sign_in('klient')
            for shipment in shipments:
                sid=shipment['id'];area=card(sid)
                area.get_by_role('button',name='Odzyskaj PIN istniejącego zakupu (TEST)',exact=True).click()
                area.get_by_label('Hasło do odzyskania PIN-u').fill(accounts['klient']['password'])
                with page.expect_response(f'**/shipments/{sid}/recover-pin-test') as response:
                    area.get_by_role('button',name='Pokaż PIN testowy',exact=True).click()
                assert response.value.status==200
                pins[sid]=response.value.json()['pin_test_only']
                area.get_by_text('PIN TESTOWY: '+pins[sid],exact=False).wait_for(state='visible')
            sign_out()
            for fulfillment,role,label in [('odbior','rolnik','Potwierdź odbiór przesyłki'),('dostawa','dostawca','Potwierdź całą przesyłkę PIN-em')]:
                shipment=next(s for s in shipments if s['fulfillment']==fulfillment)
                sid=shipment['id'];sign_in(role);area=card(sid)
                area.locator('input[placeholder="PIN klienta"]').fill(pins[sid])
                area.locator('input[type=checkbox]').check()
                with page.expect_response(f'**/shipments/{sid}/confirm') as response:
                    area.get_by_role('button',name=label,exact=True).click()
                assert response.value.status==200 and response.value.json()['confirmed']
                sign_out()
            sign_in('rolnik')
            with page.expect_response('**/farmers/me/compliance') as response:page.click('#seller-compliance-refresh')
            assert response.value.status==200 and response.value.json()['completed_transaction_count']==2
            sign_out();sign_in('admin')
            with page.expect_response('**/admin/farmers/compliance-queue?*') as response:page.click('#admin-seller-refresh')
            assert response.value.status==200 and response.value.json()['total']==1
            page.locator('#admin-seller-results textarea').fill('Sprawdzono fikcyjne demo wszystkich ról')
            with page.expect_response('**/compliance/review') as response:page.locator('#admin-seller-results button').click()
            assert response.value.status==200 and not response.value.json()['can_receive_real_payouts']
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            sign_out();assert not errors
        finally:page.close()
