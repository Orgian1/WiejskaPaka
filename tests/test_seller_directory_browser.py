"""Real HTTP seller discovery and selection on phone and desktop."""
from uuid import uuid4
from urllib.parse import urlsplit, parse_qs
import pytest
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server


@pytest.mark.parametrize('width',[320,1280])
def test_seller_alias_search_mode_and_selected_offers(delivery_browser,tmp_path,monkeypatch,width):
    monkeypatch.setenv('WP_ENABLE_SELLER_SEARCH','1')
    suffix=uuid4().hex[:8];handle='marek_'+suffix
    with server(tmp_path/'sellers.sqlite3') as client:
        actors=[]
        for role in ('rolnik','rolnik','klient'):
            data={'email':uuid4().hex+'@example.invalid','password':'SellerBrowserPrivate2026','role':role}
            result=client.post('/auth/register',json=data);assert result.status_code==201
            token=client.post('/auth/login',json=data).json()['access_token']
            actors.append((data,{'Authorization':'Bearer '+token},result.json()['id']))
        for i in range(2):
            assert client.post('/products',headers=actors[i][1],json={'name':f'Pomidory sprzedawcy {i}','stock':10,'price_grosze':200,'delivery_grosze':500}).status_code==201
        page=delivery_browser.new_page(viewport={'width':width,'height':844});page.set_default_timeout(15_000)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        def login(actor):
            page.fill('#email',actor[0]['email']);page.fill('#password',actor[0]['password'])
            page.locator('#auth button[type=submit]').click()
            page.wait_for_function('(email)=>document.querySelector("#identity").textContent.includes(email)',arg=actor[0]['email'])
        try:
            page.goto(str(client.base_url));login(actors[0])
            page.locator('#seller-login-panel').wait_for(state='visible')
            page.fill('#farm-name','Żółta Łąka '+suffix);page.fill('#farm-city','Legnica')
            with page.expect_response('**/farmers/me/profile') as response:
                page.locator('#profile-form button').click()
            assert response.value.status==200
            page.fill('#seller-public-login',handle.upper())
            with page.expect_response('**/sellers/me/login') as response:page.click('#seller-login-save')
            assert response.value.status==200
            page.get_by_text('Publiczny login zapisany: @'+handle,exact=True).wait_for(state='visible')
            assert page.locator('#seller-public-login').input_value()==handle
            assert client.put('/sellers/me/login',headers=actors[1][1],json={'login':handle.upper()}).status_code==409
            page.click('#logout');page.wait_for_function("document.querySelector('#identity').textContent==='Nie zalogowano'")
            assert page.locator('#seller-public-login').input_value()==''
            login(actors[2]);assert page.locator('#seller-login-panel').is_hidden()
            page.select_option('#catalog-search-mode','seller')
            page.fill('#catalog-query','@'+handle.upper())
            with page.expect_response(lambda r:'/sellers/search?' in r.url and parse_qs(urlsplit(r.url).query).get('q')==['@'+handle.upper()]) as response:page.click('#catalog-search-submit')
            assert response.value.status==200
            seller=page.locator('#seller-results article')
            seller.get_by_role('heading',name='@'+handle,exact=True).wait_for(state='visible')
            assert seller.count()==1
            assert actors[0][0]['email'] not in page.locator('#seller-results').inner_text()
            assert page.locator('#products').is_hidden()
            assert page.locator('#seller-previous').is_disabled() and page.locator('#seller-next').is_disabled()
            with page.expect_response('**/catalog/search?*') as response:
                seller.get_by_role('button',name='Zobacz produkty sprzedawcy @'+handle,exact=True).click()
            assert response.value.status==200
            assert 'farmer_id='+str(actors[0][2]) in response.value.url
            card=page.locator('#products > .card')
            card.get_by_text('Pomidory sprzedawcy 0',exact=True).wait_for(state='visible')
            assert card.count()==1 and 'Pomidory sprzedawcy 1' not in page.locator('#products').inner_text()
            page.locator('#catalog-seller-filter').wait_for(state='visible')
            assert page.locator('#catalog-search-mode').input_value()=='product'
            with page.expect_response('**/cart/items') as response:
                card.get_by_role('button',name='Dodaj do koszyka',exact=True).click()
            assert response.value.status==200
            with page.expect_response('**/catalog/search?*') as response:page.click('#catalog-clear-seller')
            assert response.value.status==200
            page.wait_for_function('document.querySelectorAll("#products > .card").length===2')
            page.select_option('#catalog-search-mode','seller');page.fill('#catalog-query','ZOLTA LAKA '+suffix)
            with page.expect_response(lambda r:'/sellers/search?' in r.url and parse_qs(urlsplit(r.url).query).get('q')==['ZOLTA LAKA '+suffix]) as response:page.click('#catalog-search-submit')
            assert response.value.status==200
            page.locator('#seller-results').get_by_role('heading',name='@'+handle,exact=True).wait_for(state='visible')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.set_viewport_size({'width':844,'height':390});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.click('#logout');page.wait_for_function("document.querySelector('#identity').textContent==='Nie zalogowano'")
            assert page.locator('#seller-results').inner_text()==''
            assert page.locator('#seller-public-login').input_value()==''
            assert not errors
        finally:page.close()
