"""Actual Chromium/CSP: completed history, stars, aggregate count and logout."""
import pytest
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server
from tests.test_postgres_full_api_optin import register
from tests.test_seller_ratings_http import purchase,collect

PASSWORD='Synthetic-rating-browser-password-2026!'


def login(page,url,email):
    page.goto(str(url));page.fill('#email',email);page.fill('#password',PASSWORD);page.locator('#auth button[type=submit]').click()
    page.wait_for_function('(email)=>document.querySelector("#identity").textContent===email',arg=email)


@pytest.mark.parametrize('width',[320,1280])
def test_stars_in_history_seller_summary_and_logout(delivery_browser,tmp_path,width):
    with server(tmp_path/'ratings-browser.sqlite3') as client:
        seller,sid=register(client,'rolnik',password=PASSWORD);buyer,_=register(client,'klient',password=PASSWORD)
        buyer_email=client.get('/auth/me',headers=buyer).json()['email'];seller_email=client.get('/auth/me',headers=seller).json()['email']
        received=purchase(client,buyer,seller);pending=purchase(client,buyer,seller);collect(client,buyer,seller,received)
        page=delivery_browser.new_page(viewport={'width':width,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            login(page,client.base_url,buyer_email)
            widget=page.locator('[data-rating-order="'+str(received['id'])+'"]').first
            widget.get_by_role('button',name='4 z 5 gwiazdek',exact=True).wait_for(state='visible')
            assert page.locator('[data-rating-order="'+str(pending['id'])+'"] .seller-rating-stars').count()==0
            assert widget.locator('.seller-rating-stars').bounding_box()['width']<=width
            widget.get_by_role('button',name='4 z 5 gwiazdek',exact=True).click()
            with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/seller-rating')) as reply:
                widget.get_by_role('button',name='Zapisz ocenę',exact=True).click()
            assert reply.value.status==200
            widget.get_by_text('Twoja ocena: ★★★★☆ (4/5)',exact=True).wait_for(state='visible')
            page.locator('[data-rating-seller="'+str(sid)+'"]').first.get_by_text('★ 4/5 · Liczba ocen: 1',exact=True).wait_for(state='visible')
            login(page,client.base_url,buyer_email)
            widget=page.locator('[data-rating-order="'+str(received['id'])+'"]').first
            widget.get_by_text('Twoja ocena: ★★★★☆ (4/5)',exact=True).wait_for(state='visible')
            assert widget.get_by_role('button',name='Zapisz ocenę',exact=True).count()==0
            page.locator('#logout').click()
            assert page.get_by_text('Twoja ocena: ★★★★☆ (4/5)',exact=True).count()==0
            login(page,client.base_url,seller_email)
            page.locator('#dashboard-content [data-rating-seller="'+str(sid)+'"]').get_by_text('★ 4/5 · Liczba ocen: 1',exact=True).wait_for(state='visible')
            assert not errors
        finally:page.close()
