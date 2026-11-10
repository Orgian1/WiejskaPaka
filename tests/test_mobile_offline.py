"""Kontrakt rzeczywistego renderingu bez lokalnego HTTP."""
from pathlib import Path
from scripts.check_mobile_offline import SIZES, WEB, check_offline


def test_offline_viewports_cover_mobile_and_desktop():
    assert SIZES == ((320, 700), (390, 844), (1280, 800))


def test_offline_assets_exist():
    for name in ('index.html', 'style.css', 'app.js', 'dashboard.js'):
        assert (WEB / name).is_file()


def test_offline_chromium_rendering(tmp_path):
    import pytest
    import shutil
    pytest.importorskip('playwright.sync_api')
    if not any(shutil.which(n) for n in ('chromium', 'chromium-browser', 'google-chrome')):
        pytest.skip('Brak lokalnego Chromium')
    check_offline(tmp_path)
    assert len(list(tmp_path.glob('wiejskapaka_offline_*.png'))) == 3
