"""Chromium: błędne logowanie i awaria weryfikacji konta, bez sieci.

Testuje wyłącznie interfejs z kontrolowanym mockiem API.
"""
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'
PRIVATE = ('#dashboard', '#notifications-section', '#farmer', '#farmer-details', '#orders-section')


def run():
    from playwright.sync_api import sync_playwright
    binary = next((shutil.which(n) for n in ('chromium', 'chromium-browser', 'google-chrome') if shutil.which(n)), None)
    if not binary:
        raise RuntimeError('Brak Chromium')
    html = (WEB / 'index.html').read_text(encoding='utf8')
    html = re.sub(r'<script\s+src="/assets/(?:app|dashboard)\.js"\s+defer></script>', '', html)
    html = html.replace('<link rel="stylesheet" href="/assets/style.css">', '')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=binary, args=['--no-sandbox'])
        try:
            for scenario in ('rejected_login', 'invalid_profile', 'network_error'):
                page = browser.new_page(viewport={'width': 390, 'height': 844})
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.set_content(html)
                page.add_style_tag(content=(WEB / 'style.css').read_text(encoding='utf8'))
                page.evaluate('''scenario => {
                    window.fetch = async (url) => {
                        const path=String(url);
                        if(path==='/auth/login' && scenario==='rejected_login')
                            return {ok:false,status:401,json:async()=>({detail:'Nieprawidłowe dane logowania'})};
                        if(path==='/auth/login' && scenario==='network_error')
                            throw new TypeError('Brak połączenia testowego');
                        if(path==='/auth/login')
                            return {ok:true,status:200,json:async()=>({access_token:'test-only'})};
                        if(path==='/auth/me')
                            return {ok:false,status:401,json:async()=>({detail:'Sesja wygasła'})};
                        return {ok:true,status:200,json:async()=>([])};
                    };
                }''', scenario)
                for name in ('app.js', 'dashboard.js'):
                    page.add_script_tag(content=(WEB / name).read_text(encoding='utf8'))
                page.locator('#email').fill('test@example.invalid')
                page.locator('#password').fill('HasloTestowe123!')
                page.locator('#auth button[type=submit]').click()
                expected = {'rejected_login':'Nieprawidłowe dane logowania',
                            'invalid_profile':'Sesja wygasła',
                            'network_error':'Brak połączenia testowego'}[scenario]
                page.wait_for_function('(message) => document.querySelector("#notice").textContent.includes(message)', arg=expected)
                assert page.locator('#identity').inner_text() == 'Nie zalogowano', scenario
                for selector in PRIVATE:
                    assert page.locator(selector).is_hidden(), (scenario, selector)
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), scenario
                assert not errors, (scenario, errors)
                print(f'Chromium offline auth failure {scenario}: OK')
                page.close()
        finally:
            browser.close()


if __name__ == '__main__':
    run()
