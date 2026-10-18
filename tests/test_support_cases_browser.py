"""Private case workflow on real HTTP, at phone and desktop widths."""
from pathlib import Path
import pytest
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server

@pytest.mark.parametrize('width',[320,1280])
def test_private_case_in_real_chromium(sample_browser_server,tmp_path,width):
    browser,_,_=sample_browser_server
    sample=prepare_sample(tmp_path/'support_browser');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        page=browser.new_page(viewport={'width':width,'height':844});errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        try:
            page.goto(str(client.base_url))
            def login(role):
                page.fill('#email',accounts[role]['email']);page.fill('#password',accounts[role]['password'])
                page.locator('#auth button[type=submit]').click()
                page.wait_for_function('(email)=>document.getElementById("identity").textContent.includes(email)',arg=accounts[role]['email'])
                page.locator('#dashboard-content article').first.wait_for(state='visible')
            def logout():
                page.click('#logout');page.wait_for_function("document.getElementById('identity').textContent==='Nie zalogowano'")
                assert page.locator('#support-section').is_hidden()
                assert page.locator('#support-detail').text_content()==''
                assert page.locator('#support-list').text_content()==''
            def open_case():
                with page.expect_response('**/test/support/cases?*') as response:page.click('#support-refresh')
                assert response.value.status==200
                page.get_by_role('button',name='Otwórz zgłoszenie testowe',exact=True).first.click()
                page.get_by_label('Odpowiedź testowa do zgłoszenia').wait_for(state='visible')
            login('klient')
            page.get_by_role('button',name='Zgłoś problem z zakupem (TEST)',exact=True).first.click()
            text='<img src=x onerror=alert(1)> Fikcyjny problem testowy'
            page.get_by_label('Opis problemu testowego').fill(text)
            with page.expect_response('**/test/support/cases') as response:
                page.get_by_role('button',name='Wyślij zgłoszenie testowe',exact=True).click()
            assert response.value.status==201
            page.get_by_text('Zgłoszenie testowe zapisane.',exact=False).wait_for(state='visible')
            open_case();assert text in page.locator('#support-detail').text_content()
            assert page.locator('#support-detail img').count()==0
            page.get_by_label('Odpowiedź testowa do zgłoszenia').fill('Prywatny szkic do wyczyszczenia')
            logout();login('rolnik');open_case()
            page.get_by_label('Odpowiedź testowa do zgłoszenia').fill('Fikcyjna odpowiedź sprzedawcy')
            with page.expect_response('**/test/support/cases/*/replies') as response:page.get_by_role('button',name='Zapisz odpowiedź testową',exact=True).click()
            assert response.value.status==200 and response.value.json()['case']['revision']==2
            page.locator('#support-detail').get_by_text('Fikcyjna odpowiedź sprzedawcy',exact=True).wait_for(state='visible')
            logout();login('admin');open_case()
            page.get_by_label('Nowy stan zgłoszenia testowego').select_option('closed_test')
            page.get_by_label('Odpowiedź testowa do zgłoszenia').fill('Fikcyjna decyzja testowa administratora')
            with page.expect_response('**/test/support/cases/*/replies') as response:page.get_by_role('button',name='Zapisz odpowiedź testową',exact=True).click()
            assert response.value.status==200 and response.value.json()['case']['status']=='closed_test'
            page.get_by_role('heading',name='Szczegóły zgłoszenia — Zamknięte testowo',exact=True).wait_for(state='visible')
            logout();login('klient')
            page.click('#support-refresh');page.get_by_role('button',name='Otwórz zgłoszenie testowe',exact=True).first.click()
            page.get_by_role('heading',name='Szczegóły zgłoszenia — Zamknięte testowo',exact=True).wait_for(state='visible')
            assert page.get_by_label('Odpowiedź testowa do zgłoszenia').count()==0
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.evaluate('localStorage.length')==0
            logout();login('dostawca');assert page.locator('#support-section').is_hidden()
            logout();assert not errors
        finally:page.close()
