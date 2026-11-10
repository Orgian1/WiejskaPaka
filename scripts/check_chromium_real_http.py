"""Chromium -> actual loopback HTTP -> Uvicorn/FastAPI -> disposable SQLite.

No Neon credentials, production payments, hosting, or external network.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
# Allow both `python -m scripts.<name>` and `python scripts/<name>.py`.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run():
    from playwright.sync_api import sync_playwright, Error as PlaywrightError
    from scripts.run_phone_demo import demo_environment
    binary = next((shutil.which(n) for n in ('chromium', 'chromium-browser', 'google-chrome') if shutil.which(n)), None)
    if not binary:
        return {'status': 'SKIP', 'reason': 'Chromium unavailable'}
    with tempfile.TemporaryDirectory(prefix='wp_browser_http_') as folder:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = demo_environment(os.environ, Path(folder) / 'db.sqlite3')
        proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        checks = []
        try:
            base = f'http://127.0.0.1:{port}'
            with httpx.Client(timeout=2, trust_env=False) as client:
                for _ in range(100):
                    if proc.poll() is not None:
                        raise RuntimeError('Backend exited: ' + proc.communicate()[1].decode(errors='replace')[-1500:])
                    try:
                        if client.get(base + '/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
                else:
                    raise TimeoutError('Backend startup timeout')
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=binary, args=['--no-sandbox', '--no-proxy-server'])
                try:
                    for width, height in [(390, 844), (1280, 800)]:
                        page = browser.new_page(viewport={'width': width, 'height': height})
                        errors = []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        try:
                            response = page.goto(base + '/', wait_until='networkidle', timeout=20000)
                        except PlaywrightError as exc:
                            if 'ERR_BLOCKED_BY_ADMINISTRATOR' in str(exc):
                                return {'status': 'BLOCKED', 'reason': 'Chromium navigation to loopback blocked by environment policy', 'passed': len(checks), 'checks': checks}
                            raise
                        assert response.status == 200, response.status
                        page.wait_for_selector('#products', timeout=10000)
                        assert not errors, errors
                        checks.append(f'Chromium HTTP frontend {width}x{height}')
                        if width == 390:
                            password = 'TestoweHaslo_123456789'
                            page.locator('#email').fill('real-http-rolnik@example.invalid')
                            page.locator('#password').fill(password)
                            page.locator('#role').select_option('rolnik')
                            page.locator('#register').click()
                            page.wait_for_function('document.querySelector("#notice").textContent.toLowerCase().includes("zarejestrow") || document.querySelector("#notice").textContent.toLowerCase().includes("utworzon")', timeout=10000)
                            checks.append('registration via real HTTP in Chromium')
                            page.locator('#auth button[type=submit]').click()
                            page.wait_for_function('document.querySelector("#identity").textContent.includes("(rolnik)")', timeout=10000)
                            checks.append('login via real HTTP in Chromium')
                            page.locator('#pname').fill('Marchew przez HTTP')
                            page.locator('#price').fill('3,49')
                            page.locator('#delivery').fill('5,01')
                            page.locator('#stock').fill('3')
                            page.locator('#new-product button').click()
                            page.wait_for_function('document.querySelector("#products").textContent.includes("Marchew przez HTTP")', timeout=10000)
                            checks.append('create product via real HTTP in Chromium')
                            page.locator('#logout').click()
                            page.wait_for_function('document.querySelector("#identity").textContent === "Nie zalogowano"', timeout=10000)
                            checks.append('logout via real HTTP in Chromium')
                            assert not errors, errors
                        page.close()
                finally:
                    browser.close()
        finally:
            proc.terminate()
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
    return {'status': 'PASS', 'passed': len(checks), 'checks': checks, 'scope': 'actual browser TCP HTTP to local Uvicorn and disposable SQLite'}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
