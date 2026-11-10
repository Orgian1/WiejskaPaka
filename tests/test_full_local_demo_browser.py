"""All enabled local demo panels in Chromium at phone and desktop sizes."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest
from scripts.run_phone_demo import full_demo_environment
from tests.test_address_delivery_browser import delivery_browser
from tests.test_purchase_record_http_restart import server

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def full_demo_server(tmp_path_factory):
    directory=tmp_path_factory.mktemp('full_demo_browser')/'sample'
    setup=subprocess.run([sys.executable,'-m','scripts.prepare_sample_demo','--full-demo','--directory',str(directory)],
                         cwd=ROOT,capture_output=True,text=True,timeout=120)
    assert setup.returncode==0,'Local sample preparation failed; private output withheld'
    sample=json.loads(setup.stdout)
    with patch.dict(os.environ,full_demo_environment(os.environ,Path(sample['database'])),clear=True):
        with server(Path(sample['database'])) as client:
            yield str(client.base_url),sample['credentials']


@pytest.mark.parametrize('role',['klient','rolnik','dostawca','admin'])
@pytest.mark.parametrize('width',[320,1280])
def test_complete_demo_role_panels(full_demo_server,delivery_browser,role,width):
    url,accounts=full_demo_server
    page=delivery_browser.new_page(viewport={'width':width,'height':844})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    try:
        page.goto(url)
        page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
        page.locator('#auth button[type=submit]').click()
        page.locator('#dashboard-content article').first.wait_for(state='visible')
        assert page.locator('#header-login-link').is_hidden()
        assert page.locator('#header-register-link').is_hidden()
        assert page.locator('#header-panel-link').is_visible()
        if role in ('klient','rolnik'):
            page.locator('#wallet-section').wait_for(state='visible')
        else:
            assert page.locator('#wallet-nav-link').count()==0 or page.locator('#wallet-nav-link').is_hidden()
        if role=='rolnik':page.locator('#address-delivery-panel').wait_for(state='visible')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.click('#logout')
        page.locator('#auth').wait_for(state='visible')
        assert page.locator('#header-login-link').is_visible()
        assert page.locator('#header-register-link').is_visible()
        assert page.locator('#header-panel-link').is_hidden()
        assert not errors
    finally:page.close()
