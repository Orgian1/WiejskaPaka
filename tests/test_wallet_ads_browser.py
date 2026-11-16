"""Chromium, real API/CSP: timed modal, account lifecycle and ad administration."""
from contextlib import closing
from io import BytesIO
import sqlite3
import time
from uuid import uuid4
import pytest
from PIL import Image
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server
from tests.test_wallet_ads_http import campaign

PASSWORD='Disposable-wallet-ad-browser-2026!'


def setup(client,path,role='klient'):
    email=uuid4().hex+'@example.invalid'
    body={'email':email,'password':PASSWORD,'role':role}
    uid=client.post('/auth/register',json=body).json()['id']
    admin_email=uuid4().hex+'@example.invalid'
    abody={'email':admin_email,'password':PASSWORD,'role':'klient'}
    aid=client.post('/auth/register',json=abody).json()['id']
    with closing(sqlite3.connect(path)) as con:
        con.execute("UPDATE users SET role='admin' WHERE id=?",(aid,));con.commit()
    admin={'Authorization':'Bearer '+client.post('/auth/login',json=abody).json()['access_token']}
    assert client.post('/admin/wallet-ads',headers=admin,json=campaign()).status_code==201
    return email,admin_email,admin


def login(page,url,email):
    page.goto(str(url));page.fill('#email',email);page.fill('#password',PASSWORD)
    page.locator('#auth button[type=submit]').click();page.locator('#wallet-nav-link').wait_for(state='visible')


@pytest.mark.parametrize('width',[320,1280])
@pytest.mark.parametrize('role',['klient','rolnik'])
def test_ad_countdown_automatic_entry_and_cap(delivery_browser,tmp_path,monkeypatch,width,role):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW','1');path=tmp_path/'browser.sqlite3'
    with server(path) as client:
        email,_,admin=setup(client,path,role);page=delivery_browser.new_page(viewport={'width':width,'height':844})
        page.context.route('https://example.org/**',lambda route:route.fulfill(status=200,body='Testowy reklamodawca'))
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            login(page,client.base_url,email);page.locator('#wallet-nav-link').click()
            modal=page.locator('#wallet-ad-dialog');modal.locator('img').wait_for(state='visible');started=time.monotonic()
            close=modal.get_by_role('button',name='Zamknij reklamę');assert close.is_disabled()
            assert modal.locator('[role=timer]').inner_text()=='5'
            assert modal.bounding_box()['width']<=width
            # Escape and a synthetic click cannot dismiss during the protected interval.
            page.keyboard.press('Escape');close.dispatch_event('click');assert modal.is_visible()
            modal.locator('[role=timer]').get_by_text('4',exact=True).wait_for(state='visible')
            assert close.is_disabled()
            with page.expect_popup() as popup:
                modal.locator('a').click()
            popup.value.close()
            modal.wait_for(state='detached',timeout=7000)
            assert time.monotonic()-started>=4.8
            assert page.url.endswith('#wallet-section')
            assert client.get('/admin/wallet-ads',headers=admin).json()['items'][0]['clicks']==1
            page.locator('#wallet-nav-link').click();modal.wait_for(state='detached')
            login(page,client.base_url,email);page.locator('#wallet-nav-link').click();modal.wait_for(state='detached')
            assert not errors
        finally:page.close()


def test_ad_fail_open_and_logout_account_switch(delivery_browser,tmp_path,monkeypatch):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW','1');path=tmp_path/'lifecycle.sqlite3'
    with server(path) as client:
        email,_,_=setup(client,path);page=delivery_browser.new_page()
        try:
            login(page,client.base_url,email)
            page.route('**/wallet/ads/claim',lambda route:route.abort())
            page.locator('#wallet-nav-link').click();page.locator('#wallet-ad-dialog').wait_for(state='detached')
            assert page.url.endswith('#wallet-section')
            page.unroute('**/wallet/ads/claim')
            page.route('**/wallet/ads/claim',lambda route:None)
            started=time.monotonic();page.locator('#wallet-nav-link').click()
            page.locator('#wallet-ad-dialog').wait_for(state='detached')
            assert 1.9<=time.monotonic()-started<5
            page.unroute('**/wallet/ads/claim');page.locator('#wallet-nav-link').click()
            page.locator('#wallet-ad-dialog img').wait_for(state='visible')
            # Another tab / expired session can trigger logout while the modal is open.
            page.evaluate("token=null;sessionEpoch++;logged(null)")
            assert page.locator('#wallet-ad-dialog').count()==0
            assert page.locator('#wallet-section').is_hidden()
            body={'email':uuid4().hex+'@example.invalid','password':PASSWORD,'role':'klient'}
            assert client.post('/auth/register',json=body).status_code==201
            login(page,client.base_url,body['email']);page.locator('#wallet-nav-link').click()
            page.locator('#wallet-ad-dialog img').wait_for(state='visible')
        finally:page.close()


def test_admin_campaign_form_and_edit(delivery_browser,tmp_path,monkeypatch):
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW','1');path=tmp_path/'admin.sqlite3'
    with server(path) as client:
        _,email,admin=setup(client,path);page=delivery_browser.new_page()
        try:
            page.goto(str(client.base_url));page.fill('#email',email);page.fill('#password',PASSWORD);page.locator('#auth button[type=submit]').click()
            section=page.locator('#wallet-ads-admin');section.wait_for(state='visible')
            section.get_by_role('button',name='Dodaj reklamę',exact=True).click()
            form=page.locator('#wallet-ad-editor');form.get_by_label('Nazwa reklamodawcy').fill('<img onerror=alert(1)> Bezpieczna nazwa')
            form.get_by_label('Link HTTP lub HTTPS').fill('https://example.org')
            image=BytesIO();Image.new('RGB',(100,50),'blue').save(image,'PNG')
            form.locator('input[type=file]').set_input_files({'name':'banner.png','mimeType':'image/png','buffer':image.getvalue()})
            form.get_by_label('Włącz emisję').check()
            form.get_by_role('button',name='Zapisz reklamę').click();form.wait_for(state='detached')
            section.get_by_text('<img onerror=alert(1)> Bezpieczna nazwa',exact=True).wait_for(state='visible')
            rows=client.get('/admin/wallet-ads',headers=admin).json()['items'];assert len(rows)==2
            section.get_by_role('button',name='Edytuj',exact=True).first.click()
            page.locator('#wallet-ad-editor').get_by_label('Nazwa reklamodawcy').fill('Zmieniony reklamodawca')
            page.locator('#wallet-ad-editor').get_by_role('button',name='Zapisz reklamę').click()
            section.get_by_text('Zmieniony reklamodawca',exact=True).wait_for(state='visible')
        finally:page.close()
