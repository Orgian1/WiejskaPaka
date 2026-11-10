"""Przeglądarkowe regresje widoków czterech ról (mock API)."""
import shutil
import os
from pathlib import Path
import pytest
from scripts.check_roles_offline import ROLES, WEB, run


def test_all_four_roles_covered():
    assert ROLES == ('klient', 'rolnik', 'dostawca', 'admin')


def test_browser_role_assets_present():
    assert all((WEB / filename).is_file() for filename in ('index.html', 'app.js', 'dashboard.js', 'style.css'))


def test_browser_roles_login_logout():
    if os.getenv('WIEJSKAPAKA_EXTENDED_BROWSER') != '1':
        pytest.skip('Rozszerzony test 12 scenariuszy Chromium: uruchom osobno z WIEJSKAPAKA_EXTENDED_BROWSER=1')
    pytest.importorskip('playwright.sync_api')
    if not any(shutil.which(n) for n in ('chromium','chromium-browser','google-chrome')):
        pytest.skip('Chromium nie jest zainstalowany')
    run()


def test_stale_pickup_response_is_guarded():
    js=(WEB/'app.js').read_text(encoding='utf8')
    assert 'cardEpoch===sessionEpoch' in js
    assert 'e.message!==\'SESSION_CHANGED\'' in js
    assert 'act(loadProducts)' in js
