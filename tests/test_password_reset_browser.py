"""Opt-in real Chromium reset; requires a local browser, never downloads one."""
import json
import shutil

import pytest

from tests.test_password_reset_http import enable, register, EMAIL, NEW
from tests.test_purchase_record_http_restart import server


@pytest.mark.parametrize('width', [390, 1280])
def test_reset_form_and_fragment_in_actual_chromium(monkeypatch,tmp_path,width):
    binary = next((shutil.which(name) for name in ('chromium','chromium-browser','google-chrome')
                   if shutil.which(name)),None)
    if not binary:
        pytest.skip('Local Chromium required')
    playwright = pytest.importorskip('playwright.sync_api')
    box = enable(monkeypatch,tmp_path)
    with server(tmp_path/'browser.sqlite3',reset_outbox=box) as client:
        old_session = register(client)
        with playwright.sync_playwright() as driver:
            browser = driver.chromium.launch(headless=True,executable_path=binary,
                args=['--no-sandbox','--no-proxy-server','--proxy-bypass-list=*'])
            try:
                page = browser.new_page(viewport={'width':width,'height':844})
                errors, urls = [], []
                page.on('pageerror',lambda error: errors.append(str(error)))
                page.on('request',lambda request: urls.append(request.url))
                page.goto(str(client.base_url))
                page.locator('#password-reset-section').wait_for(state='visible')
                page.fill('#reset-email',EMAIL)
                with page.expect_response('**/auth/password-reset-test/request') as response:
                    page.click('#request-reset-submit')
                assert response.value.status == 202
                files = list(box.glob('*.json'))
                assert len(files) == 1
                fragment = json.loads(files[0].read_text())['fragment']
                token = fragment.split('=',1)[1]
                page.goto(str(client.base_url)+fragment)
                page.wait_for_function("location.hash === ''")
                assert page.locator('#reset-token').input_value() == token
                page.fill('#reset-new-password',NEW)
                page.fill('#reset-repeat-password',NEW)
                with page.expect_response('**/auth/password-reset-test/confirm') as response:
                    page.click('#confirm-reset-submit')
                assert response.value.status == 200
                page.wait_for_function("document.getElementById('reset-status').textContent.includes('Hasło zmienione')")
                assert not page.locator('#reset-token').input_value()
                assert not page.locator('#reset-new-password').input_value()
                assert all(token not in url for url in urls)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert not errors
            finally:
                browser.close()
        assert client.get('/auth/me',headers=old_session).status_code == 401
        assert client.post('/auth/login',json={'email':EMAIL,'password':NEW}).status_code == 200
