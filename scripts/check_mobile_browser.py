"""Rzeczywisty smoke-test Chromium, wyłącznie na localhost i jednorazowej SQLite.

Opcjonalnie: pip install playwright oraz lokalny Chromium.
Uruchomienie: python -m scripts.check_mobile_browser
"""
import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from scripts.run_phone_demo import demo_environment

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = ((320, 700), (360, 740), (390, 844), (768, 1024), (1280, 800))
EXPECTED_NAVIGATION = ('#auth', '#nearby-section', '#products-section',
                       '#cart-section', '#farmer', '#orders-section', '#dashboard')


def horizontal_overflow_script():
    return '''() => ({viewport: window.innerWidth,
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth})'''



def find_chromium():
    return next((path for name in ('chromium', 'chromium-browser', 'google-chrome')
                 if (path := shutil.which(name))), None)


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def check_browser(screenshot_dir=None):
    """Opcjonalne zrzuty wyłącznie PUBLICZNEGO widoku, bez logowania."""
    if screenshot_dir is not None:
        screenshot_dir = Path(screenshot_dir).expanduser().resolve()
        screenshot_dir.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    binary = find_chromium()
    if not binary:
        raise RuntimeError('Brak lokalnej przeglądarki Chromium')
    with tempfile.TemporaryDirectory(prefix='wiejskapaka_chromium_') as directory:
        env = demo_environment(os.environ, Path(directory) / 'demo.sqlite3')
        port = free_port()
        address = f'http://127.0.0.1:{port}'
        process = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1',
             '--port', str(port), '--no-access-log'], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('Serwer demonstracyjny zakończył pracę')
                try:
                    with urllib.request.urlopen(address + '/', timeout=0.3) as response:
                        if response.status == 200:
                            break
                except (OSError, TimeoutError):
                    time.sleep(0.1)
            else:
                raise RuntimeError('Serwer demonstracyjny nie uruchomił się w terminie')
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, executable_path=binary,
                                                      args=['--no-sandbox', '--no-proxy-server', '--proxy-bypass-list=*'])
                try:
                    for width, height in VIEWPORTS:
                        page = browser.new_page(viewport={'width': width, 'height': height},
                                                is_mobile=width <= 390, has_touch=width <= 390)
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        failed_requests = []
                        page.on('requestfailed', lambda request: failed_requests.append(request.url))
                        try:
                            response = page.goto(address, wait_until='networkidle')
                        except Exception as exc:
                            if 'ERR_BLOCKED_BY_ADMINISTRATOR' in str(exc):
                                raise RuntimeError(
                                    'Środowisko blokuje Chromium dostęp do localhost; '
                                    'test mobilny NIE został wykonany. Uruchom na własnym komputerze.'
                                ) from exc
                            raise
                        assert response.status == 200
                        assert page.locator('h1').inner_text().find('WiejskaPaka') >= 0
                        assert page.locator('#auth').is_visible()
                        assert page.locator('#products-section').is_visible()
                        assert page.locator('#farmer').is_hidden()
                        assert page.locator('#dashboard').is_hidden()
                        # Sprawdzamy także faktyczną nawigację dotykową i fokus klawiatury.
                        links = page.locator('nav.quick-nav a')
                        assert links.evaluate_all('(links) => links.map(link => link.getAttribute("href"))') == list(EXPECTED_NAVIGATION)
                        for index in range(links.count()):
                            target = links.nth(index).get_attribute('href')
                            assert target and target.startswith('#')
                            assert page.locator(target).count() == 1, f'Nieistniejący cel: {target}'
                        page.locator('nav.quick-nav a[href="#products-section"]').click()
                        assert page.evaluate('window.location.hash') == '#products-section'
                        assert page.locator('#products-section').is_visible()
                        page.locator('#email').focus()
                        assert page.evaluate('document.activeElement.id') == 'email'
                        assert page.locator('#password').get_attribute('type') == 'password'
                        assert page.locator('#auth').locator('input[type=email]').count() == 1
                        assert not errors, f'Błędy JavaScript ({width}px): {errors}'
                        assert not failed_requests, f'Nieudane żądania ({width}px): {failed_requests}'
                        widths = page.evaluate(horizontal_overflow_script())
                        assert max(widths['document'], widths['body']) <= widths['viewport'] + 1, (
                            f'Poziome przewijanie na ekranie {width}px: {widths}')
                        if width <= 390:
                            assert page.evaluate('matchMedia("(pointer: coarse)").matches'), (
                                'Widok mobilny powinien emulować dotyk')
                        assert page.locator('html').get_attribute('lang') == 'pl'
                        assert page.locator('meta[name=viewport]').count() == 1
                        if screenshot_dir is not None:
                            page.screenshot(path=str(screenshot_dir / f'wiejskapaka_public_{width}x{height}.png'), full_page=True)
                        print(f'Chromium {width}×{height}: OK', flush=True)
                        page.close()
                finally:
                    browser.close()
        finally:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test Chromium: trzy rozmiary ekranu, bez połączenia z Neon')
    parser.add_argument('--screenshots', type=Path, default=None, metavar='KATALOG',
                        help='Zapisz zrzuty PUBLICZNEJ strony (bez logowania) w podanym katalogu')
    args = parser.parse_args()
    check_browser(screenshot_dir=args.screenshots)
