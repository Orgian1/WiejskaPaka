"""Lokalna kontrola UI + pełnego scenariusza API na jednorazowej SQLite.

Nie otwiera portu i nie łączy się z Neon. Kod strony sprawdzany statycznie,
bez symulowania renderowania na fizycznym telefonie.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from scripts.run_phone_demo import demo_environment

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ('app.js', 'dashboard.js', 'style.css')


def check_ui(client):
    page = client.get('/')
    if page.status_code != 200:
        raise AssertionError(f'Strona główna: HTTP {page.status_code}')
    html = page.text
    for marker in ('name="viewport"', 'lang="pl"', 'ŚRODOWISKO TESTOWE',
                   'id="auth"', 'id="products"', 'id="orders-section"',
                   'id="dashboard"'):
        if marker not in html:
            raise AssertionError(f'Brak elementu interfejsu: {marker}')
    for asset in ASSETS:
        response = client.get('/assets/' + asset)
        if response.status_code != 200 or not response.content:
            raise AssertionError(f'Niedostępny zasób: {asset}')
    return True


def run_checks(source=None):
    """Oddzielny proces zapobiega dziedziczeniu zaimportowanej konfiguracji API."""
    with tempfile.TemporaryDirectory(prefix='wiejskapaka_ui_check_') as directory:
        env = demo_environment(os.environ if source is None else source,
                               Path(directory) / 'ui_check.sqlite3')
        env['PYTHONPATH'] = str(ROOT)
        command = [sys.executable, '-m', 'scripts.check_demo_readiness', '--child']
        return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


def child_checks():
    from fastapi.testclient import TestClient
    from backend.app import app
    check_ui(TestClient(app))
    print('UI OK: strona, układ mobilny (metadane), panele i zasoby statyczne.', flush=True)
    # Oddzielna jednorazowa baza dla scenariusza transakcyjnego.
    result = subprocess.run([sys.executable, '-m', 'scripts.demo_journey'],
                            cwd=ROOT, env=os.environ.copy(), check=False)
    return result.returncode


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['--child']:
        return child_checks()
    if argv:
        raise SystemExit('Użycie: python -m scripts.check_demo_readiness')
    return run_checks()


if __name__ == '__main__':
    raise SystemExit(main())
