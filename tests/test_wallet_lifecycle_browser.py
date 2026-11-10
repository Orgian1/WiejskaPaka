"""Owner cancellation and admin completion through actual responsive forms."""
from contextlib import closing
import sqlite3
from uuid import uuid4
import pytest
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server
from tests.test_wallet_preview_http import deposit,set_pin,withdraw,PASSWORD
from tests.test_admin_seller_review import create_admin


@pytest.mark.parametrize('width',[320,1280])
def test_owner_cancel_admin_complete_and_logout(delivery_browser,tmp_path,monkeypatch,width):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW','1')
    database=tmp_path/'browser.sqlite3'
    with server(database) as client:
        credentials={'email':uuid4().hex+'@example.invalid','password':PASSWORD,'role':'rolnik'}
        assert client.post('/auth/register',json=credentials).status_code==201
        owner={'Authorization':'Bearer '+client.post('/auth/login',json=credentials).json()['access_token']}
        deposit(client,owner);set_pin(client,owner);withdraw(client,owner,amount=4000)
        def promote(uid):
            with sqlite3.connect(database) as con:con.execute("UPDATE users SET role='admin' WHERE id=?",(uid,))
        operator,admin_credentials=create_admin(client,promote)
        page=delivery_browser.new_page(viewport={'width':width,'height':844})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        def login(body):
            page.goto(str(client.base_url));page.fill('#email',body['email']);page.fill('#password',body['password'])
            page.locator('#auth button[type=submit]').click();page.locator('#logout').wait_for(state='visible')
        try:
            login(credentials)
            panel=page.locator('#wallet-section');panel.wait_for(state='visible')
            with page.expect_response('**/cancel-test') as response:
                panel.get_by_role('button',name='Anuluj wniosek wypłaty',exact=True).click()
            assert response.value.status==201
            panel.locator('.wallet-balances').get_by_text('100,00 zł',exact=True).wait_for(state='visible')
            panel.get_by_text('Anulowano — środki ponownie dostępne',exact=True).wait_for(state='visible')
            assert withdraw(client,owner,amount=4000).status_code==201
            page.click('#logout');login(admin_credentials)
            admin_panel=page.locator('#wallet-admin-section');admin_panel.wait_for(state='visible')
            admin_panel.get_by_text('Prowizja: 2,00 zł',exact=True).wait_for(state='visible')
            with page.expect_response('**/complete-test') as response:
                admin_panel.get_by_role('button',name='Zakończ symulację wypłaty (TEST)',exact=True).click()
            assert response.value.status==201 and response.value.json()['transfer_executed'] is False
            admin_panel.get_by_text('Brak oczekujących wniosków na tej stronie.',exact=True).wait_for(state='visible')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.click('#logout');assert admin_panel.is_hidden()
            login(credentials)
            panel.get_by_text('60,00 zł',exact=True).wait_for(state='visible')
            panel.get_by_text('Symulacja wypłaty zakończona — bez przelewu',exact=True).wait_for(state='visible')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
        finally:page.close()
