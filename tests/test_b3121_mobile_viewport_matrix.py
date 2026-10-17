"""Kontrole niezależne od dostępności Chromium i połączeń localhost."""
from pathlib import Path
from scripts.check_mobile_browser import VIEWPORTS, horizontal_overflow_script


def test_mobile_matrix_includes_small_phone_tablet_and_desktop():
    widths = [width for width, _ in VIEWPORTS]
    assert widths == sorted(set(widths))
    assert 320 in widths and 390 in widths and 768 in widths and 1280 in widths


def test_overflow_checks_both_body_and_document():
    script = horizontal_overflow_script()
    assert 'document.documentElement.scrollWidth' in script
    assert 'document.body.scrollWidth' in script
    assert 'window.innerWidth' in script


def test_browser_script_uses_touch_and_tracks_failed_requests():
    source = (Path(__file__).resolve().parents[1] / 'scripts' / 'check_mobile_browser.py').read_text()
    assert 'has_touch=width <= 390' in source
    assert "page.on('requestfailed'" in source
    assert 'not failed_requests' in source
