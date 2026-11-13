"""Real navigation, history, numbered 20-item pages and seller edit flows."""
from pathlib import Path
from datetime import date,timedelta
import pytest
from scripts.run_phone_demo import FULL_DEMO_FLAGS
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_owner_finalization import login


def sign_in_view(page,accounts,role):
    page.click('#account-nav-link')
    page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
    page.locator('#auth button[type=submit]').click()
    page.wait_for_function('(email)=>document.querySelector("#identity").textContent.includes(email)',arg=accounts[role]['email'])
    page.locator('#products-section').wait_for(state='visible')


@pytest.mark.parametrize('width',[320,360,390,768,1280])
def test_separate_routes_history_mobile_and_seller_edits(sample_browser_server,tmp_path,monkeypatch,width):
    browser,_,_=sample_browser_server
    for flag in FULL_DEMO_FLAGS:monkeypatch.setenv(flag,'1')
    sample=prepare_sample(tmp_path/'views',full_demo=True);accounts=sample['credentials']
    with server(Path(sample['database']),reset_outbox=tmp_path/'mailbox') as client:
        farmer=login(client,accounts['rolnik'])
        for i in range(43):assert client.post('/products',headers=farmer,json={'name':f'OfertaTest {i:02}','price_grosze':199,'delivery_grosze':0,'stock':10,'category_id':'vegetables','subcategory_id':'vegetables-other'}).status_code==201
        new_point=client.post('/pickup-points',headers=farmer,json={'name':'Punkt bez zamówień','city':'Opole','street':'Polna 99','opening_hours':'9:00–17:00','latitude_e6':52000000,'longitude_e6':19000000,'attendance_dates':[(date.today()+timedelta(days=2)).isoformat()]});assert new_point.status_code==201
        context=browser.new_context(viewport={'width':width,'height':950},is_mobile=width<=390,has_touch=width<=390)
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url));page.locator('#products-section').wait_for()
            assert page.locator('#account-section').is_hidden() and page.locator('#dashboard').is_hidden(),errors
            sign_in_view(page,accounts,'klient')
            page.fill('#catalog-query','OfertaTest');page.locator('#catalog-form button').click()
            page.wait_for_function('()=>document.querySelectorAll("#products > .catalog-product").length===20')
            page.locator('#catalog-pages').get_by_role('button',name='Strona produktów 2',exact=True).click()
            page.wait_for_function('()=>document.querySelector("#catalog-status").textContent.includes("Strona 2.")')
            assert page.locator('#products > .catalog-product').count()==20
            page.reload();sign_in_view(page,accounts,'klient')
            page.wait_for_function('()=>document.querySelector("#catalog-status").textContent.includes("Strona 2.")')
            assert page.locator('#catalog-query').input_value()=='OfertaTest'
            before=page.locator('#products > .catalog-product').first.inner_text()
            page.click('#cart-nav-link');page.locator('#cart-section').wait_for()
            assert page.locator('#products-section').is_hidden() and page.locator('#orders-section').is_hidden()
            page.go_back();page.locator('#products-section').wait_for()
            page.wait_for_function('()=>document.querySelector("#catalog-status").textContent.includes("Strona 2.")')
            assert page.locator('#products > .catalog-product').first.inner_text()==before
            page.go_forward();page.locator('#cart-section').wait_for()
            page.reload();page.locator('#auth').wait_for() # Tokens are deliberately memory-only.
            page.fill('#email',accounts['klient']['email']);page.fill('#password',accounts['klient']['password']);page.locator('#auth button[type=submit]').click()
            page.locator('#cart-section').wait_for();assert page.locator('#products-section').is_hidden()
            page.click('#contact-nav-link');page.locator('#contact-disclosure').wait_for()
            assert page.locator('#contact-message').is_hidden();page.click('#contact-nav-link');page.click('#footer-contact-toggle');page.locator('#contact-message').wait_for()
            page.click('#logout');sign_in_view(page,accounts,'rolnik')
            page.click('#seller-nav-link');page.locator('#seller-listings-section').wait_for()
            card=page.locator('[data-seller-listing]').first;card.wait_for()
            pid=card.get_attribute('data-seller-listing')
            card.get_by_label('Cena oferty w zł',exact=True).fill('12,34');card.get_by_label('Dostępny stan oferty',exact=True).fill('8')
            card.get_by_role('button',name='Zapisz cenę i stan',exact=True).click()
            page.wait_for_function('(id)=>[...document.querySelectorAll("[data-seller-listing]")].find(e=>e.dataset.sellerListing===id)?.textContent.includes("12,34")',arg=pid)
            saved=next(p for p in client.get('/products/mine',headers=farmer).json() if str(p['id'])==pid)
            assert saved['price_grosze']==1234 and saved['stock']==8
            page.click('#points-nav-link');page.locator('#point-location-panel').wait_for()
            assert page.locator('#point-edit-lat').get_attribute('type')=='hidden' and page.locator('#point-edit-lon').get_attribute('type')=='hidden'
            assert page.locator('#products-section').is_hidden() and page.locator('#seller-listings-section').is_hidden()
            page.locator('#point-edit-select').select_option(str(new_point.json()['id']))
            page.locator('#point-edit-name').fill('Punkt po poprawce')
            page.click('#point-edit-submit');page.wait_for_function('()=>document.querySelector("#point-edit-status").textContent.includes("Punkt zapisany")')
            assert any(p['name']=='Punkt po poprawce' for p in client.get('/farmers/me/pickup-points',headers=farmer).json())
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors
        finally:context.close()
