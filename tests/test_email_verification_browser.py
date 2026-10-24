"""Actual link, login and confirmation at phone/desktop widths; no SMTP."""
import pytest
from tests.test_address_delivery_browser import delivery_browser
from tests.test_email_verification_http import enabled, queued
from tests.test_purchase_record_http_restart import server


@pytest.mark.parametrize('width',[320,1280])
def test_fragment_removed_login_confirm_logout(delivery_browser,enabled,width):
    database,keys,key_path=enabled
    with server(database,verification_keys=key_path) as client:
        body={'email':'browser-proof@example.invalid','password':'SyntheticEmailBrowser2026!','role':'klient'}
        assert client.post('/auth/register',json=body).status_code==201
        headers={'Authorization':'Bearer '+client.post('/auth/login',json=body).json()['access_token']}
        assert client.post('/auth/email-verification/request',headers=headers).status_code==202
        secret=queued(database,keys).token
        page=delivery_browser.new_page(viewport={'width':width,'height':844});page.set_default_timeout(15000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(str(client.base_url)+'/#verify-email='+secret)
            page.wait_for_function('location.hash===""')
            page.fill('#email',body['email']);page.fill('#password',body['password'])
            page.locator('#auth button[type=submit]').click()
            page.locator('#email-verification-confirm').wait_for(state='visible')
            with page.expect_response(lambda r:'/auth/email-verification/confirm' in r.url) as result:
                page.click('#email-verification-confirm')
            assert result.value.status==200
            page.get_by_text('Adres e-mail potwierdzony.',exact=True).wait_for()
            assert client.get('/auth/email-verification/status',headers=headers).json()=={'verified':True}
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert secret not in page.content()
            assert page.evaluate('Object.values(localStorage).every(v=>!v.includes("'+secret+'"))')
            page.click('#logout');page.locator('#email-verification').wait_for(state='hidden')
            assert page.locator('#email-verification-status').inner_text()==''
            assert not errors
        finally:page.close()
