"""Actual wallet forms and logout isolation on narrow/wide Chromium."""
from uuid import uuid4
import pytest
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server


@pytest.mark.parametrize('width',[320,1280])
def test_wallet_topup_pin_withdrawal_and_logout(delivery_browser,tmp_path,monkeypatch,width):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW','1')
    password='SyntheticWalletBrowser2026!'
    with server(tmp_path/'wallet-browser.sqlite3') as client:
        email=uuid4().hex+'@example.invalid'
        assert client.post('/auth/register',json={'email':email,'password':password,'role':'klient'}).status_code==201
        page=delivery_browser.new_page(viewport={'width':width,'height':844})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            page.goto(str(client.base_url));page.fill('#email',email);page.fill('#password',password)
            page.locator('#auth button[type=submit]').click()
            panel=page.locator('#wallet-section');panel.wait_for(state='visible')
            panel.get_by_role('button',name='Doładuj portfel',exact=True).click()
            dialog=page.locator('#wallet-dialog-topup')
            assert dialog.locator('input[type=password]').count()==0
            dialog.get_by_label('Kwota (zł)').fill('100,00')
            with page.expect_response('**/wallet/topups') as response:
                dialog.get_by_role('button',name='Doładuj',exact=True).click()
            assert response.value.status==201
            panel.locator('.wallet-balances').get_by_text('100,00 zł',exact=True).wait_for(state='visible')
            panel.get_by_role('button',name='Ustaw PIN portfela',exact=True).click()
            dialog=page.locator('#wallet-dialog-pin')
            dialog.get_by_label('Hasło konta').fill(password)
            dialog.get_by_label('Nowy PIN portfela (6 cyfr)',exact=True).fill('123456')
            dialog.get_by_label('Powtórz PIN',exact=True).fill('123456')
            with page.expect_response('**/wallet/pin') as response:
                dialog.get_by_role('button',name='Zapisz PIN',exact=True).click()
            assert response.value.status==200
            panel.get_by_role('button',name='Wypłać środki',exact=True).click()
            dialog=page.locator('#wallet-dialog-withdraw')
            dialog.get_by_label('Kwota (zł)').fill('40')
            dialog.get_by_label('PIN portfela',exact=True).fill('000000')
            with page.expect_response('**/wallet/withdrawals') as response:
                dialog.get_by_role('button',name='Potwierdź wypłatę',exact=True).click()
            assert response.value.status==403
            dialog.get_by_text('Nieprawidłowy PIN portfela.',exact=True).wait_for(state='visible')
            dialog.get_by_label('PIN portfela',exact=True).fill('123456')
            with page.expect_response('**/wallet/withdrawals') as response:
                dialog.get_by_role('button',name='Potwierdź wypłatę',exact=True).click()
            assert response.value.status==201
            panel.get_by_text('60,00 zł',exact=True).wait_for(state='visible')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.click('#logout')
            assert panel.is_hidden()
            assert page.locator('[id^="wallet-dialog-"]').count()==0
            assert not errors
        finally:page.close()
