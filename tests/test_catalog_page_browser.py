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
            page.locator('#cart-items').get_by_text('Katalog testowy 049',exact=False).wait_for(state='visible')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.click('#logout')
            page.wait_for_function("document.getElementById('identity').textContent==='Nie zalogowano'")
            page.wait_for_function("!document.querySelector('#products button')")
            assert page.locator('#catalog-previous').is_disabled()
            assert not errors
        finally:page.close()
