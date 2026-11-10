"""Bounded browsing and purchase controls on a real 52-offer HTTP catalog."""
from pathlib import Path
import pytest
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server

@pytest.mark.parametrize('width',[320,1280])
def test_catalog_pages_filter_and_cart_in_chromium(sample_browser_server,tmp_path,width):
    browser,_,_=sample_browser_server;sample=prepare_sample(tmp_path/'catalog')
    accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        farmer={'Authorization':'Bearer '+client.post('/auth/login',json=accounts['rolnik']).json()['access_token']}
        for i in range(50):
            result=client.post('/products',headers=farmer,json={'name':f'Katalog testowy {i:03d}','price_grosze':349,'delivery_grosze':501,'stock':10})
            assert result.status_code==201
        page=browser.new_page(viewport={'width':width,'height':844});errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            with page.expect_response('**/catalog/search?*') as response:page.goto(str(client.base_url))
            assert response.value.status==200 and response.value.json()['total']==52
            page.wait_for_function("document.querySelectorAll('#products > .card').length===24")
            assert page.locator('#catalog-previous').is_disabled()
            for expected_offset,expected_items in [(24,24),(48,4)]:
                with page.expect_response('**/catalog/search?*') as response:page.click('#catalog-next')
                assert response.value.status==200 and response.value.json()['offset']==expected_offset
                page.wait_for_function('(n)=>document.querySelectorAll("#products > .card").length===n',arg=expected_items)
            assert page.locator('#catalog-next').is_disabled()
            with page.expect_response('**/catalog/search?*') as response:page.click('#catalog-previous')
            assert response.value.json()['offset']==24
            for text,total in [('Katalog testowy 049',1),('Brak-wyniku-syntetycznego',0),('',52)]:
                page.fill('#catalog-query',text)
                with page.expect_response('**/catalog/search?*') as response:page.locator('#catalog-form button').click()
                assert response.value.status==200 and response.value.json()['total']==total and response.value.json()['offset']==0
                page.wait_for_function('(n)=>document.querySelectorAll("#products > .card").length===n',arg=min(24,total))
            page.fill('#email',accounts['klient']['email']);page.fill('#password',accounts['klient']['password'])
            page.locator('#auth button[type=submit]').click()
            page.wait_for_function('(email)=>document.getElementById("identity").textContent.includes(email)',arg=accounts['klient']['email'])
            add=page.locator('#products > .card').first.get_by_role('button',name='Dodaj do koszyka',exact=True);add.wait_for(state='visible')
            with page.expect_response('**/cart/items') as response:add.click()
            assert response.value.status==200
            page.locator('#same-package-products article').first.wait_for(state='visible')
            page.click('#same-package-cancel')
            page.locator('#cart-items').get_by_text('Katalog testowy 049',exact=False).wait_for(state='visible')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.click('#logout')
            page.wait_for_function("document.getElementById('identity').textContent==='Nie zalogowano'")
            page.wait_for_function("!document.querySelector('#products button')")
            assert page.locator('#catalog-previous').is_disabled()
            assert not errors
        finally:page.close()


@pytest.mark.parametrize('width',[320,1280])
@pytest.mark.parametrize('direct',[False,True])
def test_same_seller_recommendations_create_one_shipment(sample_browser_server,tmp_path,width,direct):
    browser,_,_=sample_browser_server
    sample=prepare_sample(tmp_path/'one-package');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        buyer={'Authorization':'Bearer '+client.post('/auth/login',json=accounts['klient']).json()['access_token']}
        before=len(client.get('/orders/me',headers=buyer).json())
        page=browser.new_page(viewport={'width':width,'height':844});errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            page.goto(str(client.base_url))
            page.fill('#email',accounts['klient']['email']);page.fill('#password',accounts['klient']['password'])
            page.locator('#auth button[type=submit]').click()
            card=page.locator('#products > .card').filter(has_text='Marchew demonstracyjna')
            card.get_by_role('button',name='Dodaj do koszyka',exact=True).wait_for(state='visible')
            card.get_by_label('Ilość w jednostce',exact=False).fill('2')
            if direct:
                card.get_by_label('Punkt odbioru',exact=True).locator('option').first.wait_for(state='attached')
            card.get_by_role('button',name='Zamów testowo' if direct else 'Dodaj do koszyka',exact=True).click()
            dialog=page.get_by_role('dialog')
            offer=dialog.locator('article');offer.wait_for(state='visible')
            assert offer.count()==1
            assert 'Ziemniaki demonstracyjne' in offer.inner_text()
            assert 'Marchew demonstracyjna' not in dialog.locator('#same-package-products').inner_text()
            assert len(client.get('/orders/me',headers=buyer).json())==before
            offer.get_by_role('button',name='Dodaj do wspólnej paczki',exact=True).click()
            dialog.get_by_text('Dodano: Ziemniaki demonstracyjne.',exact=False).wait_for(state='visible')
            assert dialog.evaluate('(e)=>e.scrollWidth<=e.clientWidth')
            page.click('#same-package-done');assert page.get_by_role('dialog').count()==0
            page.select_option('#cart-mode','dostawa')
            page.fill('#cart-city','Legnica');page.fill('#cart-street','Testowa 1');page.fill('#cart-postal','59-220')
            with page.expect_response('**/cart/checkout-test') as response:page.click('#cart-submit')
            assert response.value.status==201
            result=response.value.json()
            assert result['delivery_grosze']==501
            assert result['total_grosze']==2*349+299+501
            assert len(client.get('/orders/me',headers=buyer).json())==before+2
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
        finally:page.close()


@pytest.mark.parametrize('width',[320,1280])
def test_customer_to_seller_switch_clears_cart_and_compacts_login(sample_browser_server,tmp_path,width):
    browser,_,_=sample_browser_server
    sample=prepare_sample(tmp_path/'account-panels');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        buyer={'Authorization':'Bearer '+client.post('/auth/login',json=accounts['klient']).json()['access_token']}
        product=client.get('/catalog/search').json()['items'][0]
        assert client.put('/cart/items',headers=buyer,json={'product_id':product['id'],'quantity':1}).status_code==200
        page=browser.new_page(viewport={'width':width,'height':844})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            page.goto(str(client.base_url))
            assert page.locator('#role option').evaluate_all('(items)=>items.map(x=>x.value)')==['klient','rolnik']
            for role in ('klient','rolnik'):
                page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
                page.locator('#auth button[type=submit]').click()
                page.wait_for_function('(email)=>document.querySelector("#identity").textContent.includes(email)',arg=accounts[role]['email'])
                assert page.locator('#auth').is_hidden()
                assert page.locator('#logout').is_visible()
                assert not page.locator('#account-security').evaluate('(node)=>node.open')
                assert page.locator('#account-section').bounding_box()['height']<150
                if role=='klient':
                    page.locator('#cart-items > .card').first.wait_for(state='visible')
                    page.click('#logout')
                    page.locator('#auth').wait_for(state='visible')
                    assert page.locator('#cart-items').inner_text()==''
                else:
                    assert page.locator('#cart-section').is_hidden()
                    assert page.locator('#cart-items').inner_text()==''
                    assert page.locator('#farmer').is_visible()
                    assert page.locator('#products-section').is_hidden()
                    assert page.locator('#nearby-section').is_hidden()
                    assert page.locator('#orders-section').bounding_box()['y']<page.locator('#farmer').bounding_box()['y']
                    assert page.locator('#new-product').is_visible()
                    assert page.locator('#seller-nav-link').is_visible()
                    assert page.locator('#account-panel-name').inner_text()=='Panel sprzedawcy'
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
        finally:page.close()
