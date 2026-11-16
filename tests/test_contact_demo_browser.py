"""Real Chromium: public contact submit, private admin mailbox, logout hygiene."""
from contextlib import closing
import json
import sqlite3
import time
from uuid import uuid4
import pytest

from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server
from tests.test_postgres_full_api_optin import register

PASSWORD='Disposable-contact-browser-2026!'


def admin_account(client,path):
    headers,uid=register(client,'klient',password=PASSWORD)
    email=client.get('/auth/me',headers=headers).json()['email']
    with closing(sqlite3.connect(path)) as con:
        con.execute("UPDATE users SET role='admin' WHERE id=?",(uid,));con.commit()
    return email


def login(page,email):
    page.fill('#email',email);page.fill('#password',PASSWORD)
    page.locator('#auth button[type=submit]').click()
    page.wait_for_function('(email)=>document.querySelector("#identity").textContent===email',arg=email)


@pytest.mark.parametrize('width',[320,1280])
def test_contact_submission_admin_plain_text_and_logout(delivery_browser,tmp_path,width):
    from playwright.sync_api import expect
    path=tmp_path/'contact.sqlite3';body='Treść kontaktu '+uuid4().hex+' <img src=x onerror=alert(1)>'
    with server(path,contact_outbox=tmp_path/'mail') as client:
        email=admin_account(client,path);page=delivery_browser.new_page(viewport={'width':width,'height':844})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url));page.locator('#footer-contact-link').click()
            expect(page.locator('#contact-submit')).to_be_enabled()
            page.fill('#contact-email','guest@example.invalid');page.fill('#contact-subject','Temat '+uuid4().hex)
            page.fill('#contact-message',body);page.locator('#footer-report-link').click()
            assert page.locator('#contact-topic').input_value()=='problem'
            assert page.locator('#contact-message').input_value()==body
            with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/test/contact/messages')) as sent:
                page.locator('#contact-submit').click()
            assert sent.value.status==202
            expect(page.locator('#contact-status')).to_contain_text('Wiadomość zapisana w skrzynce testowej administratora.')
            assert page.locator('#contact-message').input_value()==''
            assert page.locator('#contact-demo-admin').count()==0
            login(page,email)
            box=page.locator('#contact-demo-admin');box.wait_for(state='visible')
            expect(box.get_by_text(body,exact=True)).to_be_visible()
            assert box.locator('img').count()==0
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#logout').click()
            expect(page.locator('#auth')).to_be_visible()
            assert page.locator('#contact-demo-admin').count()==0
            assert body not in page.locator('body').inner_text()
            assert page.locator('#contact-email').input_value()==''
            assert not errors
        finally:page.close()


def test_late_admin_mailbox_response_cannot_render_after_logout(delivery_browser,tmp_path):
    from playwright.sync_api import expect
    path=tmp_path/'late.sqlite3'
    with server(path,contact_outbox=tmp_path/'mail') as client:
        email=admin_account(client,path);page=delivery_browser.new_page(viewport={'width':320,'height':844});pending=[]
        page.route('**/test/admin/contact/messages?*',lambda route:pending.append(route))
        try:
            page.goto(str(client.base_url));expect(page.locator('#contact-submit')).to_be_enabled();login(page,email)
            deadline=time.monotonic()+5
            while not pending and time.monotonic()<deadline:page.wait_for_timeout(25)
            assert pending
            page.locator('#logout').click()
            expect(page.locator('#auth')).to_be_visible()
            for route in pending:
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'mode':'local_test','items':[{'subject':'PRIVATE-LATE-CONTACT','topic':'contact','email':'private@example.invalid','message':'PRIVATE-LATE-CONTACT','created_at':'2026-11-16','id':'fake'}],'total':1,'has_more':False}))
            page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            assert page.locator('#contact-demo-admin').count()==0
            assert 'PRIVATE-LATE-CONTACT' not in page.locator('body').inner_text()
        finally:page.close()


def test_lost_confirmation_keeps_draft_and_retry_does_not_duplicate(delivery_browser,tmp_path):
    from playwright.sync_api import expect
    outbox=tmp_path/'mail'
    with server(tmp_path/'retry.sqlite3',contact_outbox=outbox) as client:
        page=delivery_browser.new_page(viewport={'width':320,'height':844});keys=[]
        def observe(request):
            if request.method=='POST' and request.url.endswith('/test/contact/messages'):
                keys.append(request.post_data_json['request_key'])
        page.on('request',observe)
        def lose_confirmation(route):
            assert route.fetch().status==202
            route.abort('failed')
        page.route('**/test/contact/messages',lose_confirmation)
        try:
            page.goto(str(client.base_url));page.locator('#footer-contact-link').click()
            expect(page.locator('#contact-submit')).to_be_enabled()
            page.fill('#contact-email','retry@example.invalid');page.fill('#contact-subject','Ponowienie zapisu')
            page.fill('#contact-message','Ta wiadomość ma zostać zapisana tylko jeden raz.')
            page.locator('#contact-submit').click()
            expect(page.locator('#contact-status')).to_contain_text('E-mail nie został wysłany.')
            assert page.locator('#contact-message').input_value()=='Ta wiadomość ma zostać zapisana tylko jeden raz.'
            page.unroute('**/test/contact/messages',lose_confirmation)
            page.locator('#contact-submit').click()
            expect(page.locator('#contact-status')).to_contain_text('Wiadomość zapisana w skrzynce testowej administratora.')
            assert len(keys)>=2 and len(set(keys))==1
            assert len(list(outbox.glob('*.json')))==1
        finally:page.close()
