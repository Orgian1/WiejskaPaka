"""Actual browser map geometry and promotion UI on mobile and desktop."""
from pathlib import Path
import pytest
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_owner_finalization import login


def sign_in(page,accounts,role):
    page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
    page.locator('#auth button[type=submit]').click()
    page.wait_for_function('(email)=>document.querySelector("#identity").textContent===email',arg=accounts[role]['email'])


@pytest.mark.parametrize('width',[320,1280])
def test_offline_map_address_selection_save_and_edit(sample_browser_server,tmp_path,width):
    browser,_,_=sample_browser_server;sample=prepare_sample(tmp_path/'maps');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        farmer=login(client,accounts['rolnik'])
        page=browser.new_page(viewport={'width':width,'height':900});errors=[];external=[]
        page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:external.append(r.url) if 'tile.openstreetmap.org' in r.url else None)
        try:
            page.goto(str(client.base_url));sign_in(page,accounts,'rolnik')
            page.locator('#farmer-details > details > summary').click()
            page.fill('#point-name','Nowy punkt na mapie');page.fill('#point-city','Warszawa');page.fill('#point-street','Publiczna 7');page.fill('#point-hours','9-16')
            page.click('#point-map-open')
            page.locator('#point-map.leaflet-container').wait_for(state='visible')
            page.locator('#point-map').click(position={'x':100,'y':130})
            assert page.locator('#point-map-lat').input_value() and page.locator('#point-map-lon').input_value()
            assert not external
            # Explicit configured geocoder response; no request to a real external provider.
            page.route('**/address-search/config',lambda route:route.fulfill(json={'enabled':True}))
            page.route('**/address-search',lambda route:route.fulfill(json={'items':[{'label':'Wybrany adres Warszawa','latitude_e6':52229676,'longitude_e6':21012229}]}))
            page.fill('#point-street','Publiczna 8')
            assert page.locator('#point-map-lat').input_value()==''
            page.click('#point-map-search');page.get_by_role('button',name='Wybrany adres Warszawa',exact=True).click()
            page.wait_for_function('()=>document.querySelector("#point-map-lat").value==="52,229676"')
            with page.expect_response('**/pickup-points') as response:page.click('#point-create-submit')
            assert response.value.status==201
            pid=response.value.json()['id']
            saved=next(p for p in client.get('/farmers/me/pickup-points',headers=farmer).json() if p['id']==pid)
            assert (saved['latitude_e6'],saved['longitude_e6'])==(52229676,21012229)
            page.locator('#point-location-panel > details > summary').click()
            page.select_option('#point-edit-select',str(pid));page.click('#point-edit-map-open')
            page.locator('#point-edit-map.leaflet-container').wait_for(state='visible')
            page.locator('#point-edit-map').focus();page.keyboard.press('ArrowRight')
            page.get_by_role('button',name='Wybierz środek mapy',exact=True).last.click()
            with page.expect_response('**/pickup-points/'+str(pid)) as response:page.click('#point-edit-submit')
            assert response.value.status==200
            changed=next(p for p in client.get('/farmers/me/pickup-points',headers=farmer).json() if p['id']==pid)
            assert changed['longitude_e6']!=21012229
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors and not external
        finally:page.close()


@pytest.mark.parametrize('width',[320,1280])
def test_admin_config_and_seller_promo_redemption(sample_browser_server,tmp_path,width):
    browser,_,_=sample_browser_server;sample=prepare_sample(tmp_path/'promo-ui');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        page=browser.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url));sign_in(page,accounts,'admin')
            form=page.locator('#pickup-promo-create-form');form.locator('[name=code]').fill('TRZY-DEMO')
            form.locator('[name=expires_on]').fill('2099-12-31');form.locator('[name=max_redemptions]').fill('1')
            with page.expect_response('**/admin/pickup-promotions') as response:page.click('#pickup-promo-create-submit')
            assert response.value.status==201
            settings=page.locator('#pickup-promotions-list form').filter(has_text='TRZY-DEMO');settings.wait_for()
            settings.locator('[name=max_redemptions]').fill('2')
            with page.expect_response('**/admin/pickup-promotions/TRZY-DEMO') as response:settings.get_by_role('button',name='Zapisz ustawienia kodu').click()
            assert response.value.status==200
            page.click('#logout');sign_in(page,accounts,'rolnik')
            assert page.locator('#pickup-promotions-admin').is_hidden()
            page.locator('#farmer-details > details > summary').click();page.fill('#pickup-promo-code','TRZY-DEMO')
            with page.expect_response('**/farmers/me/pickup-promotions/redeem') as response:page.click('#pickup-promo-redeem-submit')
            assert response.value.status==201 and response.value.json()['remaining']==3
            page.wait_for_function('()=>document.querySelector("#pickup-promo-status").textContent.includes(": 3.")')
            page.fill('#point-name','Promocyjny punkt');page.fill('#point-city','Legnica');page.fill('#point-street','Testowa 5');page.fill('#point-hours','9-16')
            with page.expect_response('**/pickup-points') as response:page.click('#point-create-submit')
            assert response.value.status==201 and response.value.json()['promotion']['free_until']=='2099-12-31'
            page.wait_for_function('()=>document.querySelector("#pickup-promo-status").textContent.includes(": 2.")')
            assert page.locator('#my-points').get_by_text('Promocja: darmowy do 2099-12-31',exact=False).count()==1
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors
            page.click('#logout');assert page.locator('#pickup-promo-grants').inner_text()==''
        finally:page.close()


def test_detail_tiles_failure_keeps_local_map_and_selection(sample_browser_server):
    browser,url,accounts=sample_browser_server
    page=browser.new_page(viewport={'width':320,'height':900})
    page.route('https://tile.openstreetmap.org/**',lambda route:route.abort('failed'))
    try:
        page.goto(url);sign_in(page,accounts,'rolnik')
        page.locator('#farmer-details > details > summary').click();page.click('#point-map-open')
        page.locator('#point-map.leaflet-container').wait_for(state='visible')
        page.get_by_role('button',name='Włącz szczegółową mapę ulic (OpenStreetMap)',exact=True).first.click()
        page.wait_for_function('()=>document.querySelector("#point-map-status").textContent.includes("Nie można wczytać mapy ulic")')
        page.get_by_role('button',name='Wybierz środek mapy',exact=True).first.click()
        assert page.locator('#point-map-lat').input_value() and page.locator('#point-map-lon').input_value()
        assert page.locator('#point-map svg').count()>0
    finally:page.close()
