"""Issue 59: session races, private counters, footer, GPS and large order lists."""
from pathlib import Path
import pytest
from scripts.run_phone_demo import FULL_DEMO_FLAGS
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_next_package_browser import sign_in
from tests.test_owner_finalization import login


@pytest.mark.parametrize('width',[320,1280])
def test_session_reset_race_badges_photos_and_shared_contact(sample_browser_server,tmp_path,monkeypatch,width):
    browser,_,_=sample_browser_server
    for flag in FULL_DEMO_FLAGS:monkeypatch.setenv(flag,'1')
    sample=prepare_sample(tmp_path/'issue59',full_demo=True);accounts=sample['credentials']
    with server(Path(sample['database']),reset_outbox=tmp_path/'reset-mailbox') as client:
        context=browser.new_context(viewport={'width':width,'height':950},is_mobile=width==320,has_touch=width==320)
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));pending=[]
        page.route('**/auth/password-reset-test/options',lambda route:pending.append(route))
        try:
            page.goto(str(client.base_url));sign_in(page,accounts,'klient')
            assert pending;pending.pop().fulfill(json={'enabled':True});page.unroute('**/auth/password-reset-test/options')
            page.wait_for_function('()=>document.querySelector("#password-reset-section").hidden')
            assert page.locator('#auth').is_hidden() and page.locator('#user-photo-panel').is_hidden()
            assert page.locator('#user-photo-editors input[type=file]').count()==0
            assert page.locator('input[type=file]:visible').count()==0
            assert page.locator('#favorites-count').is_hidden() and page.locator('#cart-count').is_hidden()
            card=page.locator('#products > .catalog-product').first;card.locator('.favorite-button').wait_for()
            with page.expect_response('**/favorites/*') as favorite:card.locator('.favorite-button').click()
            assert favorite.value.status==200
            page.wait_for_function('()=>document.querySelector("#favorites-count").textContent==="1"')
            card.locator('summary > b').click();body=page.locator('#catalog-details-'+card.get_attribute('data-product-id'))
            body.get_by_label('Ilość w jednostce',exact=False).fill('2')
            with page.expect_response('**/cart/items') as added:body.get_by_role('button',name='Dodaj do koszyka',exact=True).click()
            assert added.value.status==200
            page.locator('#same-package-cancel').wait_for();page.click('#same-package-cancel')
            page.wait_for_function('()=>document.querySelector("#cart-count").textContent==="1"')
            page.locator('#cart-items input').first.fill('4');page.locator('#cart-items').get_by_role('button',name='Zapisz ilość',exact=True).click()
            page.wait_for_function('()=>document.querySelector("#cart-items input").value==="4"')
            assert page.locator('#cart-count').inner_text()=='1'
            page.locator('#cart-items').get_by_role('button',name='Usuń',exact=True).click()
            page.wait_for_function('()=>document.querySelector("#cart-count").hidden')
            page.reload();sign_in(page,accounts,'klient')
            page.wait_for_function('()=>document.querySelector("#favorites-count").textContent==="1"')
            buyer=login(client,accounts['klient']);saved_ids={p['id'] for p in client.get('/favorites',headers=buyer).json()['items']}
            other=next(p['id'] for p in client.get('/products').json() if p['id'] not in saved_ids)
            assert client.put('/favorites/'+str(other),headers=buyer).status_code==200
            page.evaluate('window.dispatchEvent(new Event("focus"))')
            page.wait_for_function('()=>document.querySelector("#favorites-count").textContent==="2"')
            assert client.delete('/favorites/'+str(other),headers=buyer).status_code==200
            page.evaluate('window.dispatchEvent(new Event("focus"))')
            page.wait_for_function('()=>document.querySelector("#favorites-count").textContent==="1"')
            for actor in ['klient','rolnik']:
                if actor=='rolnik':page.click('#logout');sign_in(page,accounts,actor)
                assert page.locator('#auth').is_hidden() and page.locator('#password-reset-section').is_hidden()
                if actor=='rolnik':
                    page.locator('#user-photo-editors input[type=file]').first.wait_for(state='attached')
                    page.wait_for_function('()=>document.querySelector("#orders-count").textContent==="4"')
                    assert page.locator('#favorites-count').is_hidden()
                disclosure=page.locator('#contact-disclosure');assert not disclosure.evaluate('(e)=>e.open')
                assert page.locator('#contact-disclosure input:visible,#contact-disclosure textarea:visible').count()==0
                assert page.locator('footer > details > summary').count()==1
                page.click('#footer-contact-toggle');page.fill('#contact-message','Szkic kontaktu '+actor)
                page.click('#footer-contact-toggle');assert page.locator('#contact-message').is_hidden()
                page.click('#footer-contact-toggle');assert page.locator('#contact-message').input_value()=='Szkic kontaktu '+actor
                assert page.locator('#contact-submit').is_disabled()
            page.click('#logout');page.locator('#password-reset-section').wait_for(state='visible')
            assert not page.locator('#contact-disclosure').evaluate('(e)=>e.open') and page.locator('#contact-message').input_value()==''
            assert page.locator('#orders-count').is_hidden() and page.locator('#favorites-count').is_hidden()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors
        finally:context.close()


@pytest.mark.parametrize('width',[320,1280])
@pytest.mark.parametrize('mode',['granted','saved','denied','timeout','unavailable','missing','insecure'])
def test_nearby_navigation_saved_location_and_gps_failures(sample_browser_server,tmp_path,width,mode):
    browser,_,_=sample_browser_server;sample=prepare_sample(tmp_path/'gps-nav');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        if mode=='saved':
            buyer=login(client,accounts['klient'])
            assert client.put('/account/location',headers=buyer,json={'latitude_e6':51210000,'longitude_e6':16160000}).status_code==200
        context=browser.new_context(viewport={'width':width,'height':900},is_mobile=width==320,has_touch=width==320,geolocation={'latitude':51.21,'longitude':16.16},permissions=['geolocation'])
        context.add_init_script('''window.gpsCalls=0;const gps=navigator.geolocation;const original=gps.getCurrentPosition.bind(gps);gps.getCurrentPosition=(...args)=>{window.gpsCalls++;return original(...args)};''')
        if mode in ['denied','timeout','unavailable']:
            code={'denied':1,'timeout':3,'unavailable':2}[mode]
            context.add_init_script(f'navigator.geolocation.getCurrentPosition=(ok,fail)=>{{window.gpsCalls++;fail({{code:{code}}})}}')
        if mode=='missing':context.add_init_script('Object.defineProperty(navigator,"geolocation",{value:undefined})')
        if mode=='insecure':context.add_init_script('Object.defineProperty(window,"isSecureContext",{value:false})')
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url));sign_in(page,accounts,'klient')
            if mode=='saved':page.wait_for_function('()=>document.querySelector("#nearby-lat").value==="51,210000"')
            assert page.evaluate('window.gpsCalls')==0
            page.click('#nearby-nav-link')
            if mode in ['saved','granted']:
                page.locator('#nearby-results article').first.wait_for()
                assert page.locator('#nearby-lat').input_value()=='51,210000'
                assert page.evaluate('window.gpsCalls')==(0 if mode=='saved' else 1)
            else:
                expected={'denied':'Nie udzielono zgody','timeout':'Przekroczono czas','unavailable':'Nie udało się ustalić','missing':'Lokalizacja urządzenia jest niedostępna','insecure':'HTTPS albo localhost'}[mode]
                page.wait_for_function('(text)=>document.querySelector("#nearby-status").textContent.includes(text)',arg=expected)
                assert page.locator('#nearby-lat').input_value()=='' and page.locator('#nearby-geolocate').is_enabled()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors
        finally:context.close()


@pytest.mark.parametrize('width',[320,1280])
def test_hundreds_of_orders_are_grouped_and_rendered_in_small_pages(sample_browser_server,width):
    browser,url,accounts=sample_browser_server
    orders=[]
    for i in range(435):
        active=i<335;pickup=i<300
        orders.append({'id':1000+i,'pickup_code':'SCALE-'+str(i),'product_id':1,'product_name':'Towar '+str(i),'quantity':2,'total_grosze':598,'status':('gotowe_do_odbioru_testowo' if pickup else 'w_drodze_testowo') if active else 'odebrane','fulfillment':'odbior' if pickup else 'dostawa','pickup_point_id':11 if i<220 else 22,'pickup_point_name':'Punkt A' if i<220 else 'Punkt B'})
    page=browser.new_page(viewport={'width':width,'height':950},is_mobile=width==320,has_touch=width==320);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/orders/me',lambda route:route.fulfill(json=orders))
    page.route('**/account/navigation-counts',lambda route:route.fulfill(json={'favorites_count':0,'cart_count':0,'current_orders_count':335}))
    try:
        page.goto(url);sign_in(page,accounts,'rolnik')
        page.wait_for_function('()=>document.querySelector("#orders-count").textContent==="335"')
        groups=page.locator('#orders .seller-pickup-group');groups.last.wait_for();assert groups.count()==2
        assert page.locator('#orders [data-order-id]').count()==0
        assert groups.first.locator(':scope > summary').inner_text()=='Punkt A — 220 zamówień'
        assert groups.nth(1).locator(':scope > summary').inner_text()=='Punkt B — 80 zamówień'
        groups.first.locator(':scope > summary').click();groups.first.locator('[data-order-id]').first.wait_for()
        assert groups.first.locator('[data-order-id]').count()==20
        groups.first.get_by_role('button',name='Następne zamówienia: Punkt A',exact=True).click()
        assert groups.first.locator('[data-order-id]').first.get_attribute('data-order-id')=='1020'
        assert groups.first.locator('[data-order-id]').count()==20
        deliveries=page.locator('#orders .seller-address-orders');assert not deliveries.evaluate('(e)=>e.open')
        assert deliveries.locator(':scope > summary').inner_text()=='Dostawy na adres — 35 zamówień'
        deliveries.locator(':scope > summary').click();deliveries.locator('[data-order-id]').first.wait_for()
        assert deliveries.locator('[data-order-id]').count()==20
        page.locator('#seller-stock-summary article').first.wait_for(state='visible')
        assert 20<=page.locator('#dashboard-content > details').count()<=25
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors
    finally:page.close()
