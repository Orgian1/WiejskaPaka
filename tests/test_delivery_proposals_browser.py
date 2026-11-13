"""Seller proposes hours in the browser; only buyer consent unlocks payment."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4
import pytest
from tests.test_address_delivery_browser import delivery_browser,login
from tests.test_purchase_record_http_restart import server


@pytest.mark.parametrize('width',[320,1280])
@pytest.mark.parametrize('choice',['accepted','declined'])
def test_schedule_proposal_and_buyer_consent(delivery_browser,tmp_path,monkeypatch,width,choice):
    monkeypatch.setenv('WP_ENABLE_ADDRESS_DELIVERY','1')
    day=datetime.now(ZoneInfo('Europe/Warsaw')).date()+timedelta(days=7)
    with server(tmp_path/'proposals.sqlite3') as client:
        accounts=[];headers=[]
        for role in ('rolnik','klient'):
            body={'email':uuid4().hex+'@example.invalid','password':'SyntheticProposalBrowser2026!','role':role}
            assert client.post('/auth/register',json=body).status_code==201
            headers.append({'Authorization':'Bearer '+client.post('/auth/login',json=body).json()['access_token']});accounts.append(body)
        product=client.post('/products',headers=headers[0],json={'name':'Produkt z nowym terminem','price_grosze':200,'delivery_grosze':500,'stock':5}).json()['id']
        window=client.post('/address-delivery/windows',headers=headers[0],json={'city':'Legnica','postal_code':'59-220','weekday':day.weekday(),'from_time':'10:00','to_time':'16:00'}).json()['id']
        receipt=client.post('/orders',headers=headers[1],json={'product_id':product,'quantity':1,'fulfillment':'dostawa','delivery_city':'Legnica','delivery_street':'Testowa 7','delivery_postal_code':'59-220','address_delivery':{'window_id':window,'delivery_date':day.isoformat(),'available_from':'12:00','available_to':'18:00','phone':'+48 500 100 200'}})
        assert receipt.status_code==201;oid=receipt.json()['id']
        seller=delivery_browser.new_page(viewport={'width':width,'height':900},is_mobile=width==320,has_touch=width==320);buyer=delivery_browser.new_page(viewport={'width':width,'height':900},is_mobile=width==320,has_touch=width==320)
        errors=[]
        for page in (seller,buyer):page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            login(seller,str(client.base_url),accounts[0]);login(buyer,str(client.base_url),accounts[1])
            card=seller.locator('#delivery-requests article').first
            card.get_by_label('Nowa data dostawy',exact=True).fill((day+timedelta(days=1)).isoformat())
            card.get_by_label('Nowy termin od godziny',exact=True).fill('08:00');card.get_by_label('Nowy termin do godziny',exact=True).fill('09:00')
            with seller.expect_response(f'**/address-delivery/requests/{oid}/proposal') as result:card.get_by_role('button',name='Zaproponuj termin klientowi',exact=True).click()
            assert result.value.status==200;proposal=result.value.json()['proposal']
            event={'event_id':uuid4().hex,'event_type':'payment_success_test'}
            assert client.post(f'/test/payments/{oid}/events',headers=headers[1],json=event).status_code==409
            buyer.click('#delivery-view-refresh')
            buyer.locator('#delivery-requests').get_by_text('08:00–09:00',exact=False).wait_for()
            label='Akceptuję proponowany termin' if choice=='accepted' else 'Odrzucam proponowany termin'
            with buyer.expect_response('**/address-delivery/proposals/'+proposal['id']+'/decision') as result:buyer.get_by_role('button',name=label,exact=True).click()
            assert result.value.status==200 and result.value.json()['state']==choice
            rows=client.get('/address-delivery/requests/mine',headers=headers[1]).json()['items']
            assert rows[0]['state']==('accepted' if choice=='accepted' else 'pending')
            assert client.post(f'/test/payments/{oid}/events',headers=headers[1],json=event).status_code==(200 if choice=='accepted' else 409)
            assert client.get(f'/products/{product}').json()['stock']==4
            assert rows[0]['total_grosze']==700
            for page in (seller,buyer):
                assert '500100200' not in page.locator('#delivery-requests').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
        finally:seller.close();buyer.close()
