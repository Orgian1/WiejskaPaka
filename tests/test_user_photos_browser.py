"""Real file picker and HTTP uploads on mobile/desktop; synthetic images only."""
import io
from uuid import uuid4
import pytest
from PIL import Image
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server


@pytest.mark.parametrize('width',[320,1280])
def test_photo_upload_replace_error_delete_and_logout(delivery_browser,tmp_path,monkeypatch,width):
    print('PHOTO_STAGE test entered',flush=True)
    monkeypatch.setenv('WP_ENABLE_USER_PHOTOS','1')
    with server(tmp_path/'photos.sqlite3') as client:
        print('PHOTO_STAGE server ready',flush=True)
        account={'email':uuid4().hex+'@example.invalid','password':'SyntheticPhotoBrowser2026','role':'rolnik'}
        assert client.post('/auth/register',json=account).status_code==201
        headers={'Authorization':'Bearer '+client.post('/auth/login',json=account).json()['access_token']}
        assert client.post('/products',headers=headers,json={'name':'Pomidor ze zdjęciem','stock':5,'price_grosze':200,'delivery_grosze':500}).status_code==201
        print('PHOTO_STAGE accounts and product ready',flush=True)
        page=delivery_browser.new_page(viewport={'width':width,'height':844})
        page.set_default_timeout(15_000)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            print('PHOTO_STAGE page navigation',flush=True)
            page.goto(str(client.base_url));page.fill('#email',account['email']);page.fill('#password',account['password'])
            page.locator('#auth button[type=submit]').click()
            print('PHOTO_STAGE login submitted',flush=True)
            page.locator('#user-photo-panel').wait_for(state='visible')
            print('PHOTO_STAGE editors visible',flush=True)
            stream=io.BytesIO();Image.new('RGB',(2400,1600),'green').save(stream,'PNG')
            for label in ('Zdjęcie profilowe','Zdjęcie gospodarstwa','Produkt: Pomidor ze zdjęciem'):
                print('PHOTO_STAGE target '+label,flush=True)
                card=page.locator('#user-photo-editors article').filter(has=page.get_by_role('heading',name=label,exact=True))
                card.locator('input[type=file]').set_input_files({'name':'synthetic.png','mimeType':'image/png','buffer':stream.getvalue()})
                with page.expect_response(lambda r:r.request.method=='PUT' and '/user-photos/' in r.url) as response:
                    card.get_by_role('button',name='Zapisz zdjęcie',exact=True).click()
                print('PHOTO_STAGE upload response',flush=True)
                assert response.value.status==200
                print('PHOTO_STAGE status checked',flush=True)
                assert response.value.json()['bytes']<=1_000_000
                print('PHOTO_STAGE JSON checked',flush=True)
                card.locator('img').wait_for(state='visible')
                print('PHOTO_STAGE image visible',flush=True)
                page.wait_for_function('Array.from(document.querySelectorAll("#user-photo-editors img")).every(i=>i.complete&&i.naturalWidth>0)')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                print('PHOTO_STAGE image rendered',flush=True)
                old_src=card.locator('img').get_attribute('src')
                card.locator('input[type=file]').set_input_files({'name':'bad.png','mimeType':'image/png','buffer':b'broken'})
                with page.expect_response(lambda r:r.request.method=='PUT' and '/user-photos/' in r.url) as response:
                    card.get_by_role('button',name='Zapisz zdjęcie',exact=True).click()
                print('PHOTO_STAGE invalid response',flush=True)
                assert response.value.status==422
                card.get_by_text('Nie zapisano zmiany.',exact=False).wait_for(state='visible')
                assert card.locator('img').get_attribute('src')==old_src
                with page.expect_response(lambda r:r.request.method=='DELETE' and '/user-photos/' in r.url) as response:
                    card.get_by_role('button',name='Usuń zdjęcie',exact=True).click()
                assert response.value.status==200
                print('PHOTO_STAGE deletion response',flush=True)
                page.wait_for_function('(label)=>Array.from(document.querySelectorAll("#user-photo-editors article")).find(c=>c.querySelector("h3").textContent===label)?.querySelectorAll("img").length===0',arg=label)
            print('PHOTO_STAGE logout',flush=True)
            page.click('#logout');page.locator('#user-photo-panel').wait_for(state='hidden')
            assert page.locator('#user-photo-editors').inner_text()==''
            assert not errors
        finally:
            print('PHOTO_STAGE closing page',flush=True)
            page.close()
            print('PHOTO_STAGE page closed',flush=True)
