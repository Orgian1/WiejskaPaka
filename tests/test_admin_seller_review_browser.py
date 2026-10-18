"""Actual browser + real HTTP for a disposable, explicitly provisioned test admin."""
import shutil
import sqlite3
import pytest
from tests.test_purchase_record_http_restart import server,account
from tests.test_admin_seller_review import create_admin
from backend.seller_compliance import RULES_VERSION

@pytest.mark.parametrize('width',[320,1280])
def test_admin_queue_decision_browser(tmp_path,width):
    binary=next((shutil.which(n) for n in ('chromium','chromium-browser','google-chrome') if shutil.which(n)),None)
    if not binary:pytest.skip('Local Chromium required')
    playwright=pytest.importorskip('playwright.sync_api')
    database=tmp_path/'browser.sqlite3'
    with server(database) as client:
        def promote(uid):
            with sqlite3.connect(database) as con:con.execute("UPDATE users SET role='admin' WHERE id=?",(uid,))
        admin,body=create_admin(client,promote)
        farmer=account(client,'rolnik')
        assert client.post('/farmers/me/compliance/acknowledge',headers=farmer,json={'rules_version':RULES_VERSION,'accepted':True}).status_code==200
        with playwright.sync_playwright() as driver:
            browser=driver.chromium.launch(headless=True,executable_path=binary,args=['--no-sandbox','--no-proxy-server','--proxy-bypass-list=*'])
            try:
                page=browser.new_page(viewport={'width':width,'height':844})
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(str(client.base_url));assert page.locator('#admin-seller-review').is_hidden()
                page.fill('#email',body['email']);page.fill('#password',body['password'])
                page.locator('#auth button[type=submit]').click()
                page.locator('#admin-seller-review').wait_for(state='visible')
                with page.expect_response('**/admin/farmers/compliance-queue?*') as response:page.click('#admin-seller-refresh')
                assert response.value.status==200
                page.locator('#admin-seller-results textarea').wait_for(state='visible')
                page.locator('#admin-seller-results textarea').fill('Fikcyjna decyzja w demo')
                with page.expect_response('**/compliance/review') as response:page.locator('#admin-seller-results button').click()
                assert response.value.status==200
                page.wait_for_function("document.getElementById('admin-seller-status').textContent.includes('Decyzja testowa zapisana')")
                assert page.locator('#admin-seller-results textarea').count()==0
                assert client.get('/farmers/me/compliance',headers=farmer).json()['review_status']=='approved'
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.click('#logout');page.locator('#admin-seller-review').wait_for(state='hidden')
                assert page.locator('#admin-seller-status').text_content()==''
                assert not errors
            finally:browser.close()
