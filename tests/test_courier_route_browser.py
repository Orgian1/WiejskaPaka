"""Courier routes use only assigned active addresses and clear after completion."""
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import pytest
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_owner_finalization import login
from tests.test_next_package_browser import sign_in


@pytest.mark.parametrize('width',[320,1280])
def test_courier_route_deduplicates_and_rechecks_before_opening(sample_browser_server,tmp_path,width):
    browser,_,_=sample_browser_server
    sample=prepare_sample(tmp_path/'courier-route');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        courier=login(client,accounts['dostawca']);buyer=login(client,accounts['klient'])
        addresses=client.get('/couriers/me/active-addresses',headers=courier).json()
        assert len(addresses)==2
        expected=', '.join(filter(None,[addresses[0]['delivery_street'],addresses[0]['delivery_postal_code'],addresses[0]['delivery_city'],'Polska']))
        assert client.get('/couriers/me/active-addresses',headers=buyer).status_code==403
        page=browser.new_page(viewport={'width':width,'height':900},is_mobile=width==320,has_touch=width==320);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url));sign_in(page,accounts,'dostawca')
            area=page.get_by_role('region',name='Trasa aktywnych dostaw')
            assert area.locator('li').count()==0
            area.get_by_role('button',name='Pokaż trasę aktywnych dostaw',exact=True).click()
            area.locator('li').wait_for();assert area.locator('li').count()==1
            assert area.locator('li').inner_text()==expected
            area.get_by_role('button',name='Przejdź do nawigacji dostaw',exact=True).click()
            link=area.get_by_role('link',name='Otwórz sprawdzoną trasę w Mapach Google')
            link.wait_for();url=urlsplit(link.get_attribute('href'))
            assert url.hostname=='www.google.com' and parse_qs(url.query)['destination']==[expected]
            assert link.get_attribute('rel')=='noopener noreferrer' and 'phone' not in link.get_attribute('href')
            shipment=next(s for s in client.get('/shipments/mine',headers=buyer).json()['shipments'] if s['fulfillment']=='dostawa')
            pin=client.post('/shipments/'+shipment['id']+'/recover-pin-test',headers=buyer,json={'password':accounts['klient']['password']}).json()['pin_test_only']
            assert client.post('/shipments/'+shipment['id']+'/confirm',headers=courier,json={'pin':pin}).json()['confirmed']
            area.get_by_role('button',name='Przejdź do nawigacji dostaw',exact=True).click()
            area.get_by_text('Brak aktywnych adresów dostaw.',exact=True).wait_for()
            assert area.locator('a,li').count()==0
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors
            page.click('#logout');assert page.get_by_role('region',name='Trasa aktywnych dostaw').count()==0
        finally:page.close()
