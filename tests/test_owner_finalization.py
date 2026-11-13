"""Owner acceptance: own pickup groups and a one-time PIN without a checkbox."""
from pathlib import Path
import pytest
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_sample_demo_browser import sample_browser_server


def login(client, credentials):
    response=client.post('/auth/login',json=credentials)
    assert response.status_code==200
    return {'Authorization':'Bearer '+response.json()['access_token']}


def test_pickup_summary_and_pin_without_extra_confirmation(tmp_path):
    sample=prepare_sample(tmp_path/'owner-pin')
    with server(Path(sample['database'])) as client:
        headers={r:login(client,c) for r,c in sample['credentials'].items()}
        orders=client.get('/orders/me',headers=headers['rolnik']).json()
        pickups=[o for o in orders if o['fulfillment']=='odbior']
        assert len(pickups)==2
        assert len({o['pickup_point_id'] for o in pickups})==1
        assert all(o['product_name'] and o['quantity']>0 and o['pickup_point_name'] for o in pickups)
        assert not any(k in o for o in orders for k in ('phone','buyer_phone','email','pin_hash'))
        shipments=client.get('/shipments/mine',headers=headers['klient']).json()['shipments']
        for shipment in shipments:
            sid=shipment['id']
            pin=client.post(f'/shipments/{sid}/recover-pin-test',headers=headers['klient'],
                json={'password':sample['credentials']['klient']['password']}).json()['pin_test_only']
            actor='rolnik' if shipment['fulfillment']=='odbior' else 'dostawca'
            url=f'/shipments/{sid}/confirm'
            assert client.post(url,headers=headers['klient'],json={'pin':pin}).status_code==403
            response=client.post(url,headers=headers[actor],json={'pin':pin})
            assert response.status_code==200 and response.json()['confirmed']
            assert client.post(url,headers=headers[actor],json={'pin':pin}).status_code==409


@pytest.mark.parametrize('width',[320,1280])
def test_inline_catalog_and_seller_groups_browser(sample_browser_server,width):
    browser,url,accounts=sample_browser_server
    page=browser.new_page(viewport={'width':width,'height':900})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    try:
        page.goto(url)
        card=page.locator('#products > details').first
        card.locator('summary').wait_for()
        assert not card.evaluate('(e)=>e.open')
        initial_url=page.url
        card.locator('summary').focus();page.keyboard.press('Enter')
        assert card.evaluate('(e)=>e.open') and page.url==initial_url
        page.fill('#email',accounts['rolnik']['email']);page.fill('#password',accounts['rolnik']['password'])
        page.locator('#auth button[type=submit]').click()
        group=page.locator('.seller-pickup-group').first
        group.wait_for(state='visible')
        assert not group.evaluate('(e)=>e.open')
        group.locator(':scope > summary').click()
        assert group.locator('li').count()==2
        assert 'ilość:' in group.inner_text()
        assert page.get_by_text('Klient sprawdził produkty',exact=True).count()==0
        assert page.get_by_text('Klient sprawdził towar',exact=True).count()==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors
    finally:page.close()


@pytest.mark.parametrize('width',[320,1280])
def test_favorite_heart_is_persistent_and_does_not_expand_card(sample_browser_server,width):
    browser,url,accounts=sample_browser_server
    page=browser.new_page(viewport={'width':width,'height':900})
    try:
        page.goto(url)
        page.fill('#email',accounts['klient']['email']);page.fill('#password',accounts['klient']['password'])
        page.locator('#auth button[type=submit]').click()
        heart=page.locator('#products .favorite-button').first
        heart.wait_for(state='visible')
        page.wait_for_function("() => (document.querySelector('#favorites-status').textContent.length>0)")
        if heart.get_attribute('aria-pressed')=='true':
            heart.click();page.wait_for_function("() => (document.querySelector('#products .favorite-button').getAttribute('aria-pressed')==='false')")
        card=page.locator('#products > details').first
        assert not card.evaluate('(e)=>e.open')
        with page.expect_response('**/favorites/*') as response:heart.click()
        assert response.value.status==200
        page.wait_for_function("() => (document.querySelector('#products .favorite-button').getAttribute('aria-pressed')==='true')")
        assert not card.evaluate('(e)=>e.open')
        product_id=heart.get_attribute('data-favorite-product')
        page.locator('#favorites-results .favorite-button[data-favorite-product="'+product_id+'"]').wait_for()
        page.reload()
        page.fill('#email',accounts['klient']['email']);page.fill('#password',accounts['klient']['password'])
        page.locator('#auth button[type=submit]').click()
        page.wait_for_function("() => (document.querySelector('#products .favorite-button')?.getAttribute('aria-pressed')==='true')")
        page.locator('#favorites-results .favorite-button[data-favorite-product="'+product_id+'"]').click()
        page.wait_for_function("() => (document.querySelector('#products .favorite-button').getAttribute('aria-pressed')==='false')")
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    finally:page.close()


def test_paid_pickup_is_ready_without_seller_approval_and_pin_is_single_use(tmp_path):
    sample=prepare_sample(tmp_path/'paid-pickup')
    with server(Path(sample['database'])) as client:
        buyer=login(client,sample['credentials']['klient']);farmer=login(client,sample['credentials']['rolnik'])
        product=client.get('/products').json()[0]
        point=client.get('/farmers/me/pickup-points',headers=farmer).json()[0]
        for cancel in (False,True):
            response=client.post('/orders',headers=buyer,json={'product_id':product['id'],'quantity':1,'fulfillment':'odbior','pickup_point_id':point['id']})
            assert response.status_code==201
            order=response.json();oid=order['id'];payment_url=f'/test/payments/{oid}/events'
            payload={'event_id':'owner-paid','event_type':'payment_success_test'}
            assert client.post(payment_url,headers=buyer,json=payload).status_code==200
            assert client.post(payment_url,headers=buyer,json=payload).status_code==200
            state=next(o for o in client.get('/orders/me',headers=buyer).json() if o['id']==oid)
            assert state['status']=='gotowe_do_odbioru_testowo'
            assert client.post(payment_url,headers=buyer,json={**payload,'event_id':'another-event'}).status_code==409
            if cancel:
                url=f'/orders/{oid}/cancel-paid-test'
                first=client.post(url,headers=buyer);second=client.post(url,headers=buyer)
                assert first.status_code==second.status_code==200
                assert first.json()['refund_grosze']==second.json()['refund_grosze']==order['total_grosze']
                assert second.json()['already_processed']
            else:
                url=f'/orders/{oid}/confirm';payload={'pin':order['pin_test_only']}
                response=client.post(url,headers=farmer,json=payload)
                assert response.status_code==200 and response.json()['confirmed']
                assert client.post(url,headers=farmer,json=payload).status_code==409


@pytest.mark.parametrize('width',[320,1280])
def test_saved_gps_location_seller_navigation_and_default_panels(sample_browser_server,tmp_path,width):
    from urllib.parse import urlsplit,parse_qs
    browser,_,_=sample_browser_server
    sample=prepare_sample(tmp_path/'navigation-location');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        farmer=login(client,accounts['rolnik']);buyer=login(client,accounts['klient'])
        result=client.post('/pickup-points',headers=farmer,json={'name':'Drugi punkt testowy','city':'Legnica','street':'Testowa 9','opening_hours':'9-16'})
        assert result.status_code==201
        context=browser.new_context(viewport={'width':width,'height':900},geolocation={'latitude':52.229676,'longitude':21.012229},permissions=['geolocation'])
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        def sign_in(role):
            page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
            page.locator('#auth button[type=submit]').click()
            page.wait_for_function('(email)=>document.querySelector("#identity").textContent===email',arg=accounts[role]['email'])
        try:
            page.goto(str(client.base_url));sign_in('klient')
            page.get_by_role('button',name='Zapamiętaj wybraną lokalizację na koncie').wait_for()
            page.click('#nearby-geolocate')
            page.wait_for_function('()=>document.querySelector("#nearby-lat").value.length>0')
            with page.expect_response('**/account/location') as response:page.get_by_role('button',name='Zapamiętaj wybraną lokalizację na koncie').click()
            assert response.value.status==200
            assert client.get('/account/location',headers=buyer).json()['location']=={'latitude_e6':52229676,'longitude_e6':21012229}
            page.reload();sign_in('klient')
            page.wait_for_function('()=>document.querySelector("#nearby-lat").value==="52,229676"')
            with page.expect_response('**/account/location') as response:page.get_by_role('button',name='Usuń zapamiętaną lokalizację').click()
            assert response.value.status==200 and client.get('/account/location',headers=buyer).json()['location'] is None
            page.click('#logout');sign_in('rolnik')
            page.locator('#seller-point-menu li').first.wait_for(state='attached')
            assert not page.locator('#farmer-details > details').evaluate('(e)=>e.open')
            assert page.locator('#farmer > details').evaluate('(e)=>e.open')
            assert page.locator('#orders-section').is_visible()
            page.locator('#seller-point-nav > summary').click()
            page.get_by_role('button',name='Przesuń wyżej: Drugi punkt testowy',exact=True).click()
            assert 'Drugi punkt testowy' in page.locator('#seller-point-menu li').first.inner_text()
            link=page.get_by_role('link',name='Przejdź do nawigacji',exact=True)
            parsed=urlsplit(link.get_attribute('href'));params=parse_qs(parsed.query)
            assert parsed.hostname=='www.google.com' and params['api']==['1']
            assert params['waypoints']==['Testowa 9, Legnica, Polska']
            page.locator('#seller-point-menu').get_by_role('link',name='Dodaj punkt',exact=True).click()
            assert page.locator('#farmer-details > details').evaluate('(e)=>e.open')
            assert page.locator('#point-name').evaluate('(e)=>e===document.activeElement')
            page.reload();sign_in('rolnik')
            page.wait_for_function('()=>document.querySelector("#seller-point-menu li")?.textContent.includes("Drugi punkt testowy")')
            assert not page.locator('#farmer-details > details').evaluate('(e)=>e.open')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
        finally:context.close()
