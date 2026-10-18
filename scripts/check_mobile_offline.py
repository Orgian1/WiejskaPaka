"""Rzeczywisty rendering Chromium bez połączeń sieciowych (mockowane API).

Uruchom: python -m scripts.check_mobile_offline [--screenshots KATALOG]
Nie jest to test serwera ani integracji API.
"""
import argparse
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'
SIZES = ((320, 700), (390, 844), (1280, 800))


def check_offline(screenshot_dir=None):
    from playwright.sync_api import sync_playwright
    binary = next((shutil.which(n) for n in ('chromium', 'chromium-browser', 'google-chrome') if shutil.which(n)), None)
    if not binary:
        raise RuntimeError('Brak Chromium w systemie')
    if screenshot_dir is not None:
        screenshot_dir = Path(screenshot_dir).resolve()
        screenshot_dir.mkdir(parents=True, exist_ok=True)
    html = (WEB / 'index.html').read_text(encoding='utf-8')
    html = re.sub(r'<script\s+src="/assets/(?:app|dashboard)\.js"\s+defer></script>', '', html)
    html = html.replace('<link rel="stylesheet" href="/assets/style.css">', '')
    css = (WEB / 'style.css').read_text(encoding='utf-8')
    scripts = [(WEB / name).read_text(encoding='utf-8') for name in ('app.js', 'dashboard.js')]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=binary, args=['--no-sandbox'])
        try:
            for width, height in SIZES:
                page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.set_content(html, wait_until='load')
                page.add_style_tag(content=css)
                page.evaluate('''() => {
                    window.fetch = async (url) => {
                        const path = String(url);
                        const data = path.startsWith('/catalog/search?') ? {items:[],total:0,limit:24,offset:0} :
                                     path === '/products' ? [] :
                                     path === '/orders/me' ? [] :
                                     path === '/notifications' ? [] : [];
                        return {ok:true, status:200, json:async()=>data};
                    };
                }''')
                for script in scripts:
                    page.add_script_tag(content=script)
                page.wait_for_timeout(150)
                assert not errors, f'Błędy JS {width}px: {errors}'
                assert page.locator('h1').is_visible()
                assert page.locator('#auth').is_visible()
                for selector in ('#farmer', '#farmer-details', '#orders-section', '#dashboard', '#notifications-section'):
                    assert page.locator(selector).is_hidden(), f'Widoczny prywatny panel {selector}'
                expected_navigation = ('#auth', '#nearby-section', '#products-section', '#cart-section', '#orders-section', '#dashboard')
                assert page.locator('nav.quick-nav a').count() == len(expected_navigation)
                assert page.locator('nav.quick-nav a').evaluate_all('(links) => links.map(link => link.getAttribute("href"))') == list(expected_navigation)
                for link in page.locator('nav.quick-nav a').all():
                    target = link.get_attribute('href')
                    assert target.startswith('#') and page.locator(target).count() == 1
                page.locator('nav.quick-nav a').nth(2).click()
                assert page.evaluate('location.hash') == '#products-section'
                page.locator('#email').focus()
                assert page.evaluate('document.activeElement.id') == 'email'
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), f'Overflow {width}px'
                if screenshot_dir is not None:
                    page.screenshot(path=str(screenshot_dir / f'wiejskapaka_offline_{width}x{height}.png'), full_page=True)
                print(f'Chromium offline {width}×{height}: OK')
                page.close()
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    check_offline(args.screenshots)
