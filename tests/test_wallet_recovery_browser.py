"""Real delayed/lost responses and failed PIN recovery at phone/desktop widths."""
import time
from uuid import uuid4
import pytest
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server
from tests.test_wallet_preview_http import PASSWORD,deposit,set_pin
from tests.test_wallet_withdrawal_lifecycle import wallet_db,audit


def owner_account(client):
    body={'email':uuid4().hex+'@example.invalid','password':PASSWORD,'role':'klient'}
    uid=client.post('/auth/register',json=body).json()['id']
    headers={'Authorization':'Bearer '+client.post('/auth/login',json=body).json()['access_token']}
    return body,headers,uid


def login(page,url,body):
    page.goto(url);page.fill('#email',body['email']);page.fill('#password',body['password'])
    page.locator('#auth button[type=submit]').click();page.locator('#wallet-section').wait_for(state='visible')
    return page.locator('#wallet-section')


def wait_routes(page,routes,count):
    deadline=time.monotonic()+15
    while len(routes)<count and time.monotonic()<deadline:page.wait_for_timeout(25)
    assert len(routes)>=count


@pytest.mark.parametrize('width',[320,1280])
@pytest.mark.parametrize('mode',['late','late_success','lost'])
def test_recovery_of_delayed_or_lost_topup(delivery_browser,wallet_db,width,mode):
    with server(wallet_db) as client:
        body,owner,uid=owner_account(client)
        page=delivery_browser.new_page(viewport={'width':width,'height':844})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        held=[]
        def intercept(route):
            if mode in ('late','late_success'):
                upstream=route.fetch() if mode=='late_success' and not held else None
                held.append((route,upstream))
            else:route.fetch();route.abort()
        try:
            panel=login(page,str(client.base_url),body)
            page.route('**/wallet/topups',intercept)
            panel.get_by_role('button',name='Doładuj portfel',exact=True).click()
            dialog=page.locator('#wallet-dialog-topup');dialog.get_by_label('Kwota (zł)').fill('100')
            dialog.get_by_role('button',name='Doładuj',exact=True).click()
            key=f'wp-wallet-intent-v1:{uid}:topup'
            if mode!='lost':wait_routes(page,held,1)
            else:
                # Function polling preserves the application CSP without unsafe-eval.
                page.wait_for_function("() => document.querySelector('#wallet-dialog-topup [role=alert]').textContent.length>0")
                assert client.get('/wallet',headers=owner).json()['available_grosze']==10000
            with page.expect_response('**/wallet/operations/reconcile-test') as response:
                dialog.get_by_role('button',name='Sprawdź poprzednią operację',exact=True).click()
            assert response.value.status==200
            assert response.value.json()['outcome']==('released' if mode=='late' else 'committed')
            dialog.wait_for(state='hidden')
            assert page.evaluate('(key)=>sessionStorage.getItem(key)',key) is None
            if mode!='lost':
                panel.get_by_role('button',name='Doładuj portfel',exact=True).click()
                fresh=page.locator('#wallet-dialog-topup');fresh.get_by_label('Kwota (zł)').fill('50')
                fresh.get_by_role('button',name='Doładuj',exact=True).click();wait_routes(page,held,2)
                new_key=page.evaluate('(key)=>JSON.parse(sessionStorage.getItem(key)).request_key',key)
                with page.expect_response('**/wallet/topups') as old:
                    if mode=='late_success':held[0][0].fulfill(response=held[0][1])
                    else:held[0][0].continue_()
                assert old.value.status==(201 if mode=='late_success' else 409);old.value.finished()
                assert page.evaluate('(key)=>JSON.parse(sessionStorage.getItem(key)).request_key',key)==new_key
                assert fresh.get_by_role('button',name='Doładuj',exact=True).is_disabled()
                with page.expect_response('**/wallet/topups') as new:
                    held[1][0].continue_()
                assert new.value.status==201
            expected={'late':5000,'lost':10000,'late_success':15000}[mode]
            panel.locator('.wallet-balances').get_by_text({'late':'50,00 zł','lost':'100,00 zł','late_success':'150,00 zł'}[mode],exact=True).wait_for(state='visible')
            state=client.get('/wallet',headers=owner).json()
            assert state['available_grosze']==expected and len(state['entries'])==(2 if mode=='late_success' else 1)
            assert page.evaluate('(key)=>sessionStorage.getItem(key)',key) is None
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
            audit(wallet_db)
        finally:page.close()


@pytest.mark.parametrize('width',[320,1280])
def test_failed_pin_can_be_recovered_before_changing_amount(delivery_browser,wallet_db,width):
    with server(wallet_db) as client:
        body,owner,uid=owner_account(client);deposit(client,owner);set_pin(client,owner)
        page=delivery_browser.new_page(viewport={'width':width,'height':844})
        try:
            panel=login(page,str(client.base_url),body)
            panel.get_by_role('button',name='Wypłać środki',exact=True).click()
            dialog=page.locator('#wallet-dialog-withdraw');dialog.get_by_label('Kwota (zł)').fill('40')
            dialog.get_by_label('PIN portfela',exact=True).fill('000000')
            with page.expect_response('**/wallet/withdrawals') as response:
                dialog.get_by_role('button',name='Potwierdź wypłatę',exact=True).click()
            assert response.value.status==403
            dialog.get_by_label('Kwota (zł)').fill('50');dialog.get_by_label('PIN portfela',exact=True).fill('123456')
            dialog.get_by_role('button',name='Potwierdź wypłatę',exact=True).click()
            dialog.get_by_text('Najpierw sprawdź poprzednią operację przyciskiem poniżej.',exact=True).wait_for(state='visible')
            with page.expect_response('**/wallet/operations/reconcile-test') as recovery:
                dialog.get_by_role('button',name='Sprawdź poprzednią operację',exact=True).click()
            assert recovery.value.status==200 and recovery.value.json()['outcome']=='released'
            dialog.wait_for(state='hidden')
            panel.get_by_role('button',name='Wypłać środki',exact=True).click()
            dialog=page.locator('#wallet-dialog-withdraw');dialog.get_by_label('Kwota (zł)').fill('50')
            dialog.get_by_label('PIN portfela',exact=True).fill('123456')
            with page.expect_response('**/wallet/withdrawals') as response:
                dialog.get_by_role('button',name='Potwierdź wypłatę',exact=True).click()
            assert response.value.status==201
            dialog.wait_for(state='hidden')
            state=client.get('/wallet',headers=owner).json()
            assert (state['available_grosze'],state['reserved_grosze'])==(5000,5000)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            audit(wallet_db)
        finally:page.close()
