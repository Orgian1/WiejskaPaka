"""Row-wide product disclosure, seller defaults and visible per-point statuses."""
from pathlib import Path
import pytest
from scripts.run_phone_demo import FULL_DEMO_FLAGS
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_owner_finalization import login


def sign_in(page,accounts,role):
    page.click('#account-nav-link');page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
    page.locator('#auth button[type=submit]').click()
    page.wait_for_function('(email)=>document.querySelector("#identity").textContent===email',arg=accounts[role]['email'])


@pytest.mark.parametrize('width',[320,1280])
def test_details_span_the_selected_row_and_survive_resize_and_logout(sample_browser_server,tmp_path,width):
    browser,_,_=sample_browser_server;sample=prepare_sample(tmp_path/'rows');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        farmer=login(client,accounts['rolnik'])
        for i in range(5):assert client.post('/products',headers=farmer,json={'name':f'Produkt w rzędzie {i}','price_grosze':250,'delivery_grosze':0,'stock':10}).status_code==201
        page=browser.new_page(viewport={'width':width,'height':900},is_mobile=width==320,has_touch=width==320);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url));sign_in(page,accounts,'klient')
            cards=page.locator('#products > .catalog-product');cards.first.locator('.favorite-button').wait_for()
            heart=cards.first.locator('.favorite-button')
            with page.expect_response('**/favorites/*') as favorite:
                heart.tap() if width==320 else heart.click()
            assert favorite.value.status==200
            page.wait_for_function('()=>document.querySelector("#products .favorite-button").getAttribute("aria-pressed")==="true"')
            assert not cards.first.evaluate('(e)=>e.open')
            if width==320:assert page.evaluate('matchMedia("(pointer:coarse)").matches')
            chosen=cards.nth(1);chosen.locator('summary > b').tap() if width==320 else chosen.locator('summary > b').click()
            pid=chosen.get_attribute('data-product-id')
            body=page.locator('#catalog-details-'+pid);body.wait_for(state='visible')
            def assert_row():
                page.wait_for_function('''(pid)=>{
                    const host=document.querySelector('#products'),cards=[...host.querySelectorAll(':scope > .catalog-product')];
                    const n=getComputedStyle(host).gridTemplateColumns.split(/\\s+/).filter(Boolean).length;
                    const index=cards.findIndex(c=>c.dataset.productId===pid),last=Math.min(cards.length-1,Math.floor(index/n)*n+n-1);
                    const panel=document.querySelector('#catalog-details-'+pid);
                    return cards[last].nextElementSibling===panel&&panel.getBoundingClientRect().width>=host.getBoundingClientRect().width-2;
                }''',arg=pid)
                assert body.bounding_box()['y']>=chosen.bounding_box()['y']+chosen.bounding_box()['height']-1
            assert_row();page.set_viewport_size({'width':1280 if width==320 else 320,'height':900});assert_row()
            cards.nth(2).locator('summary > b').click()
            page.wait_for_function('()=>document.querySelectorAll(".catalog-row-details:not([hidden])").length===1')
            page.wait_for_function('()=>!document.querySelectorAll("#products > .catalog-product")[1].open')
            assert not chosen.evaluate('(e)=>e.open')
            active=page.locator('.catalog-row-details:not([hidden])')
            active.get_by_label('Sposób realizacji').select_option('dostawa');active.get_by_label('Miejscowość dostawy',exact=True).fill('Prywatny szkic')
            page.evaluate('()=>{window.oldCatalogInputs=[...document.querySelectorAll(".catalog-row-details input")]}')
            page.click('#logout')
            assert page.evaluate('()=>window.oldCatalogInputs.every(i=>i.value==="")')
            assert page.locator('.catalog-row-details:not([hidden])').count()==0
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors
        finally:page.close()


@pytest.mark.parametrize('width',[320,1280])
def test_only_orders_and_restock_open_and_point_groups_include_statuses(sample_browser_server,tmp_path,monkeypatch,width):
    browser,_,_=sample_browser_server
    for flag in FULL_DEMO_FLAGS:monkeypatch.setenv(flag,'1')
    sample=prepare_sample(tmp_path/'seller-defaults',full_demo=True);accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        farmer=login(client,accounts['rolnik']);orders=client.get('/orders/me',headers=farmer).json()
        page=browser.new_page(viewport={'width':width,'height':900},is_mobile=width==320,has_touch=width==320);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url));sign_in(page,accounts,'rolnik')
            page.click('#orders-nav-link')
            assert page.locator('#orders-section').is_visible()
            assert page.locator('#farmer').is_hidden()
            for panel in ('wallet-section','farmer-details','point-location-panel','seller-compliance','user-photo-panel','notifications-section','favorites-section'):
                assert page.locator('#'+panel).is_hidden(),panel
            group=page.locator('#orders .seller-pickup-group').first;group.locator(':scope > summary').click()
            assert '2 zamówienia' in group.locator(':scope > summary').inner_text()
            for order in [o for o in orders if o['fulfillment']=='odbior']:
                item=group.get_by_text(f"#{order['id']} ({order['pickup_code']})",exact=False)
                item.wait_for(state='visible')
                assert item.count()==1 and 'ilość:' in item.inner_text() and 'Gotowe do odbioru' in item.inner_text()
            assert '500100200' not in group.inner_text()
            buyer=login(client,accounts['klient'])
            shipment=next(s for s in client.get('/shipments/mine',headers=buyer).json()['shipments'] if s['fulfillment']=='odbior')
            recovered=client.post('/shipments/'+shipment['id']+'/recover-pin-test',headers=buyer,json={'password':accounts['klient']['password']})
            assert recovered.status_code==200
            group.get_by_label('PIN przesyłki '+shipment['id'],exact=True).fill(recovered.json()['pin_test_only'])
            with page.expect_response('**/shipments/'+shipment['id']+'/confirm') as confirmation:
                group.get_by_role('button',name='Potwierdź odbiór całej przesyłki',exact=True).click()
            assert confirmation.value.status==200 and confirmation.value.json()['confirmed']
            assert client.post('/shipments/'+shipment['id']+'/confirm',headers=farmer,json={'pin':recovered.json()['pin_test_only']}).status_code==409
            page.click('#wallet-nav-link');page.locator('#wallet-section').wait_for(state='visible')
            page.reload();sign_in(page,accounts,'rolnik');page.click('#wallet-nav-link');page.locator('#wallet-section').wait_for(state='visible')
            assert page.locator('#dashboard').is_hidden()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors
        finally:page.close()
