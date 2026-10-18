"""Test interakcji ról w rzeczywistym Chromium, z kontrolowanym mockiem API.

Nie testuje rzeczywistego serwera, bazy ani autoryzacji backendu.
Uruchom: python -m scripts.check_roles_offline
"""
from pathlib import Path
import re
import shutil

WEB = Path(__file__).resolve().parents[1] / 'web'
ROLES = ('klient', 'rolnik', 'dostawca', 'admin')

MOCK = r'''() => {
  window.__requests = [];
  window.fetch = async (url, options={}) => {
    const path = String(url);
    window.__requests.push({path, method:options.method||'GET'});
    const role = window.__mockRole;
    let result = [];
    if(path==='/auth/login') result={access_token:'mock-token'};
    else if(path==='/auth/me') result={email:'test@example.invalid',role};
    else if(path==='/farmers/me/profile') result={farm_name:'Gospodarstwo testowe',city:'Testowo',description:''};
    else if(path.startsWith('/catalog/search?')) result={items:[{id:1,name:'Marchew',price_grosze:350,delivery_grosze:200,stock:10,farmer_id:8}],total:1,limit:24,offset:0};
    else if(path==='/products') result=[{id:1,name:'Marchew',price_grosze:350,delivery_grosze:200,stock:10,farmer_id:8}];
    else if(path==='/farmers/8/pickup-points') result=[{id:3,name:'Punkt',city:'Testowo',street:'Polna 1',opening_hours:'9-17'}];
    else if(path==='/orders/me') result=[];
    else if(path==='/products/mine') result=[];
    else if(path==='/couriers/me/orders') result=[];
    else if(path==='/notifications/me') result=[];
    else if(path==='/farmers/me/pickup-points') result=[];
    else if(path==='/test/farmers/me/payout-report') result={mode:'test'};
    else if(path==='/auth/logout') result={ok:true};
    return {ok:true,status:200,json:async()=>result};
  };
}'''


def run():
    from playwright.sync_api import sync_playwright
    binary = next((shutil.which(name) for name in ('chromium', 'chromium-browser', 'google-chrome') if shutil.which(name)), None)
    if not binary:
        raise RuntimeError('Brak Chromium')
    html = (WEB/'index.html').read_text(encoding='utf8')
    html = re.sub(r'<script\s+src="/assets/(?:app|dashboard)\.js"\s+defer></script>', '', html)
    html = html.replace('<link rel="stylesheet" href="/assets/style.css">', '')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=binary, args=['--no-sandbox'])
        try:
            for width in (320, 390, 1280):
                for role in ROLES:
                    page = browser.new_page(viewport={'width':width,'height':844})
                    errors=[]
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.set_content(html)
                    page.add_style_tag(content=(WEB/'style.css').read_text(encoding='utf8'))
                    page.evaluate(MOCK)
                    page.evaluate('(r) => window.__mockRole=r', role)
                    for name in ('app.js','dashboard.js'):
                        page.add_script_tag(content=(WEB/name).read_text(encoding='utf8'))
                    page.locator('#email').fill('test@example.invalid')
                    page.locator('#password').fill('HasloTestowe123!')
                    page.locator('#auth button[type=submit]').click()
                    page.wait_for_function("document.querySelector('#identity').textContent.includes('Zalogowano:')")
                    page.wait_for_timeout(100)
                    assert page.locator('#dashboard').is_visible(), (role,width)
                    assert page.locator('#notifications-section').is_visible(), (role,width)
                    assert page.locator('#farmer').is_visible() == (role=='rolnik'), (role,width)
                    assert page.locator('#farmer-details').is_visible() == (role=='rolnik'), (role,width)
                    assert page.locator('#orders-section').is_visible() == (role!='dostawca'), (role,width)
                    assert page.locator('#dashboard-title').inner_text() == {
                        'klient':'Panel klienta','rolnik':'Panel rolnika',
                        'dostawca':'Panel dostawcy','admin':'Panel administratora'}[role]
                    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (role,width)
                    assert not errors, (role,width,errors)
                    page.locator('#logout').click()
                    page.wait_for_function("document.querySelector('#identity').textContent==='Nie zalogowano'")
                    assert page.locator('#dashboard').is_hidden()
                    assert page.locator('#notifications-section').is_hidden()
                    assert page.locator('#farmer').is_hidden()
                    assert page.locator('#orders-section').is_hidden()
                    assert page.locator('#dashboard-content').inner_text()==''
                    assert page.locator('#notifications-list').inner_text()==''
                    assert not errors, (role,width,errors)
                    print(f'Chromium role={role} viewport={width}: OK')
                    page.close()
        finally:
            browser.close()

if __name__=='__main__':
    run()
