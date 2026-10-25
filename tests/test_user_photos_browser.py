"""Real file picker and HTTP uploads on mobile/desktop; synthetic images only."""
import io
from uuid import uuid4
import pytest
from PIL import Image
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server


@pytest.mark.parametrize('width',[320,1280])
def test_photo_upload_replace_error_delete_and_logout(delivery_browser,tmp_path,monkeypatch,width):
    monkeypatch.setenv('WP_ENABLE_USER_PHOTOS','1')
    with server(tmp_path/'photos.sqlite3') as client:
        account={'email':uuid4().hex+'@example.invalid','password':'SyntheticPhotoBrowser2026','role':'rolnik'}
        assert client.post('/auth/register',json=account).status_code==201
        headers={'Authorization':'Bearer '+client.post('/auth/login',json=account).json()['access_token']}
        assert client.post('/products',headers=headers,json={'name':'Pomidor ze zdjęciem','stock':5,'price_grosze':200,'delivery_grosze':500}).status_code==201
        page=delivery_browser.new_page(viewport={'width':width,'height':844})
        page.set_default_timeout(15_000)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            page.goto(str(client.base_url));page.fill('#email',account['email']);page.fill('#password',account['password'])
            page.locator('#auth button[type=submit]').click()
            page.locator('#user-photo-panel').wait_for(state='visible')
            stream=io.BytesIO();Image.new('RGB',(2400,1600),'green').save(stream,'PNG')
            for label in ('Zdjęcie profilowe','Zdjęcie gospodarstwa','Produkt: Pomidor ze zdjęciem'):
                card=page.locator('#user-photo-editors article').filter(has=page.get_by_role('heading',name=label,exact=True))
                card.locator('input[type=file]').set_input_files({'name':'synthetic.png','mimeType':'image/png','buffer':stream.getvalue()})
                with page.expect_response(lambda r:r.request.method=='PUT' and '/user-photos/' in r.url) as response:
                    card.get_by_role('button',name='Zapisz zdjęcie',exact=True).click()
                assert response.value.status==200
                stored=client.get(response.value.url)
                assert stored.status_code==200 and stored.headers['content-type']=='image/jpeg'
                assert 0<len(stored.content)<=1_000_000
                card.locator('img').wait_for(state='visible')
                page.wait_for_function('Array.from(document.querySelectorAll("#user-photo-editors img")).every(i=>i.complete&&i.naturalWidth>0)')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                old_src=card.locator('img').get_attribute('src')
                card.locator('input[type=file]').set_input_files({'name':'bad.png','mimeType':'image/png','buffer':b'broken'})
                with page.expect_response(lambda r:r.request.method=='PUT' and '/user-photos/' in r.url) as response:
                    card.get_by_role('button',name='Zapisz zdjęcie',exact=True).click()
                assert response.value.status==422
                card.get_by_text('Nie zapisano zmiany.',exact=False).wait_for(state='visible')
                assert card.locator('img').get_attribute('src')==old_src
                with page.expect_response(lambda r:r.request.method=='DELETE' and '/user-photos/' in r.url) as response:
                    card.get_by_role('button',name='Usuń zdjęcie',exact=True).click()
                assert response.value.status==200
                page.wait_for_function('(label)=>Array.from(document.querySelectorAll("#user-photo-editors article")).find(c=>c.querySelector("h3").textContent===label)?.querySelectorAll("img").length===0',arg=label)
            page.fill('#pname','Marchew ze zdjęciem');page.fill('#price','3,50')
            page.fill('#delivery','0');page.fill('#stock','12')
            page.locator('#product-photo-file').set_input_files({'name':'carrot.png','mimeType':'image/png','buffer':stream.getvalue()})
            with page.expect_response('**/products/with-photo') as created:
                page.locator('#new-product').get_by_role('button',name='Dodaj produkt',exact=True).click()
            assert created.value.status==201
            inventory=page.get_by_role('region',name='Stan produktów gospodarstwa')
            item=inventory.locator('article').filter(has=page.get_by_role('heading',name='Marchew ze zdjęciem',exact=True))
            item.get_by_text('Dostępne w magazynie: 12 szt.',exact=True).wait_for(state='visible')
            item.locator('img').wait_for(state='visible')
            assert len(client.get(f"/user-photos/product/{created.value.json()['id']}").content)<=500_000
            assert page.locator('#product-photo-file').input_value()==''
            page.click('#logout');page.locator('#user-photo-panel').wait_for(state='hidden')
            assert page.locator('#user-photo-editors').inner_text()==''
            assert not errors
        finally:
            page.close()
