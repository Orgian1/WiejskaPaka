"""Real HTTP/browser role gating and explicit consent on narrow and wide screens."""
import shutil
from uuid import uuid4
import pytest
from tests.test_purchase_record_http_restart import server

@pytest.mark.parametrize('width',[320,1280])
def test_seller_consent_in_chromium(tmp_path,width):
    binary=next((shutil.which(n) for n in ('chromium','chromium-browser','google-chrome') if shutil.which(n)),None)
    if not binary:pytest.skip('Local Chromium required')
    playwright=pytest.importorskip('playwright.sync_api')
    with server(tmp_path/'browser.sqlite3') as client:
        email=uuid4().hex+'@example.invalid'
        password='Private-seller-demo-123!'
        assert client.post('/auth/register',json={'email':email,'password':password,'role':'rolnik'}).status_code==201
        with playwright.sync_playwright() as driver:
            browser=driver.chromium.launch(headless=True,executable_path=binary,args=['--no-sandbox','--no-proxy-server','--proxy-bypass-list=*'])
            try:
                page=browser.new_page(viewport={'width':width,'height':844})
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(str(client.base_url))
                assert page.locator('#seller-compliance').is_hidden()
                page.fill('#email',email);page.fill('#password',password)
                page.locator('#auth button[type=submit]').click()
                page.locator('#seller-compliance').wait_for(state='visible')
                page.click('#seller-compliance-refresh')
                page.wait_for_function("document.getElementById('seller-compliance-status').textContent.includes('Zakończone transakcje: 0')")
                assert page.locator('#seller-rules-submit').is_disabled()
                page.check('#seller-rules-check')
                with page.expect_response('**/farmers/me/compliance/acknowledge') as response:
                    page.click('#seller-rules-submit')
                assert response.value.status==200
                page.wait_for_function("document.getElementById('seller-compliance-status').textContent.includes('Zasady demo potwierdzone')")
                assert page.locator('#seller-rules-submit').is_disabled()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.click('#logout')
                page.locator('#seller-compliance').wait_for(state='hidden')
                assert page.locator('#seller-compliance-status').text_content()==''
                assert not errors
            finally:browser.close()
