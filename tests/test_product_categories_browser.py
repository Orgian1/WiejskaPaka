"""Real seller/client taxonomy flows and catalog geometry on three device sizes."""
import io
from pathlib import Path
import pytest
from PIL import Image
from scripts.run_phone_demo import FULL_DEMO_FLAGS
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_next_package_browser import sign_in
from tests.test_owner_finalization import login


@pytest.mark.parametrize('width',[320,768,1280])
def test_categories_create_edit_filters_favorites_rows_cart_and_location(sample_browser_server,tmp_path,monkeypatch,width):
    browser,_,_=sample_browser_server
    for flag in FULL_DEMO_FLAGS:monkeypatch.setenv(flag,'1')
    sample=prepare_sample(tmp_path/'catalog-categories',full_demo=True);accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        farmer=login(client,accounts['rolnik']);buyer=login(client,accounts['klient'])
        before_orders=client.get('/orders/me',headers=buyer).json()
        unavailable=client.post('/products',headers=farmer,json={'name':'Jabłka niedostępne','stock':0,'price_grosze':299,'delivery_grosze':0,'category_id':'fruit','subcategory_id':'fruit-apples'})
        assert unavailable.status_code==201
        context=browser.new_context(viewport={'width':width,'height':950},is_mobile=width==320,has_touch=width==320,geolocation={'latitude':51.21,'longitude':16.16},permissions=['geolocation'])
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url));sign_in(page,accounts,'rolnik')
            page.click('#seller-nav-link');page.locator('#product-category option').last.wait_for(state='attached')
            page.select_option('#product-category','vegetables');page.select_option('#product-subcategory','vegetables-tomatoes')
            page.fill('#pname','Specjalne pomidory');page.fill('#price','3,99');page.fill('#delivery','5,01');page.fill('#stock','4');page.fill('#product-description','<b>Opis pomidorów</b>')
            photo=io.BytesIO();Image.new('RGB',(500,400),'red').save(photo,format='JPEG')
            page.set_input_files('#product-photo-file',{'name':'tomatoes.jpg','mimeType':'image/jpeg','buffer':photo.getvalue()})
            with page.expect_response('**/products/with-photo') as created:page.locator('#new-product button[type=submit],#new-product > button').click()
            assert created.value.status==201;pid=created.value.json()['id']
            assert client.get('/user-photos/product/'+str(pid)).status_code==200
            editor=page.locator('[data-product-editor="'+str(pid)+'"]');editor.locator('summary').click()
            assert client.patch('/products/mine/'+str(pid),headers=farmer,json={'stock':3}).status_code==200
            editor.get_by_label('Opis produktu',exact=True).fill('Opis po edycji')
            with page.expect_response('**/products/mine/'+str(pid)) as edited:editor.get_by_role('button',name='Zapisz produkt',exact=True).click()
            assert edited.value.status==200 and edited.value.json()['description']=='Opis po edycji'
            assert edited.value.json()['stock']==3 and edited.value.request.post_data_json=={'description':'Opis po edycji'}
            assert client.get('/orders/me',headers=buyer).json()==before_orders
            page.click('#logout');sign_in(page,accounts,'klient')
            buttons=page.locator('#catalog-category-bar button');buttons.last.wait_for()
            assert buttons.count()==17 and buttons.first.inner_text()=='Wszystkie'
            assert page.locator('#catalog-subcategory-field').is_hidden()
            page.get_by_role('button',name='Warzywa',exact=True).click()
            page.select_option('#catalog-subcategory','vegetables-tomatoes')
            page.fill('#catalog-query','Specjalne');page.locator('#catalog-search-submit').click()
            page.wait_for_function('()=>document.querySelectorAll("#products > .catalog-product").length===1')
            card=page.locator('#products > .catalog-product');card.locator('summary > b').wait_for();assert card.locator('summary > b').inner_text()=='Specjalne pomidory'
            assert page.get_by_role('button',name='Warzywa',exact=True).get_attribute('aria-pressed')=='true'
            with page.expect_response('**/favorites/*') as saved:card.locator('.favorite-button').click()
            assert saved.value.status==200
            page.wait_for_function('()=>document.querySelector("#products .favorite-button").getAttribute("aria-pressed")==="true"')
            assert not card.evaluate('(e)=>e.open')
            card.locator('summary > b').click();details=page.locator('#catalog-details-'+str(pid));details.get_by_text('Opis po edycji',exact=True).wait_for()
            assert details.bounding_box()['width']>=page.locator('#products').bounding_box()['width']-2
            with page.expect_response('**/cart/items') as cart:details.get_by_role('button',name='Dodaj do koszyka',exact=True).click()
            assert cart.value.status==200
            page.locator('#same-package-cancel').wait_for(state='visible');page.click('#same-package-cancel')
            page.check('#catalog-available');page.select_option('#catalog-fulfillment','odbior')
            page.select_option('#catalog-sort','nearest');page.locator('#catalog-location-prompt').wait_for(state='visible')
            with page.expect_response(lambda r:r.url.endswith('/catalog/query') and r.request.post_data_json.get('sort')=='nearest') as nearest:page.click('#catalog-use-gps')
            assert nearest.value.status==200 and nearest.value.json()['items'][0]['distance_m']>=0
            page.wait_for_function('()=>document.querySelectorAll("#products > .catalog-product").length===1')
            page.click('#favorites-nav-link');page.locator('#favorites-results article').filter(has_text='Specjalne pomidory').get_by_role('button',name='Pokaż w katalogu',exact=True).click()
            page.wait_for_function('()=>document.querySelector("#catalog-category-bar button").getAttribute("aria-pressed")=="true"')
            assert page.locator('#catalog-sort').input_value()=='newest'
            assert page.locator('#catalog-subcategory-field').is_hidden()
            page.fill('#catalog-query','');page.locator('#catalog-search-submit').click()
            page.get_by_role('button',name='Owoce',exact=True).click();page.uncheck('#catalog-available')
            page.wait_for_function('()=>document.querySelector("#products")?.textContent.includes("Jabłka niedostępne")')
            empty=page.locator('#products > .catalog-product').filter(has_text='Jabłka niedostępne');empty.locator('summary > b').click()
            empty_details=page.locator('#catalog-details-'+str(unavailable.json()['id']))
            assert empty_details.get_by_role('button',name='Dodaj do koszyka',exact=True).is_disabled()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.locator('#catalog-category-bar').evaluate('(e)=>e.scrollWidth>e.clientWidth')
            assert not errors
        finally:context.close()
