"""Calendar selection and saved attendance through the actual seller UI."""
import pytest
from backend import pickup_dates
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server, account


@pytest.mark.parametrize('width',[320,1280])
def test_seller_calendar_and_orders_layout(delivery_browser,tmp_path,monkeypatch,width):
    monkeypatch.setenv('WP_ENABLE_PICKUP_DATES','1')
    with server(tmp_path/'calendar-browser.sqlite') as client:
        body={'email':'calendar-seller@example.invalid','password':'SyntheticCalendar2026!','role':'rolnik'}
        assert client.post('/auth/register',json=body).status_code==201
        page=delivery_browser.new_page(viewport={'width':width,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url))
            page.fill('#email',body['email']);page.fill('#password',body['password']);page.locator('#auth button[type=submit]').click()
            page.locator('#farmer-details').wait_for(state='visible')
            assert page.locator('#products-section').is_hidden()
            assert page.locator('#nearby-section').is_hidden()
            assert page.locator('#cart-section').is_hidden()
            assert page.locator('#orders-section').bounding_box()['y']<page.locator('#farmer').bounding_box()['y']
            day=pickup_dates.today().isoformat()
            button=page.locator(f'#point-calendar button[aria-label="{day}"]')
            button.wait_for(state='visible');button.click()
            assert page.locator(f'#point-calendar button[aria-label="{day}"]').get_attribute('aria-pressed')=='true'
            for name,value in [('name','Rynek'),('city','Legnica'),('street','Polna 1'),('hours','10:00–12:00')]:page.fill('#point-'+name,value)
            with page.expect_response(lambda r:r.url.endswith('/pickup-points') and r.request.method=='POST') as result:
                page.locator('#point-form > button').click()
            assert result.value.status==201
            assert result.value.request.post_data_json['attendance_dates']==[day]
            page.locator('#my-points').get_by_text(day,exact=False).wait_for()
            page.locator(f'#point-edit-calendar button[aria-label="{day}"][aria-pressed="true"]').wait_for(state='visible')
            page.click('#logout')
            assert page.locator('#point-edit-calendar').inner_text()==''
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors
        finally:page.close()
