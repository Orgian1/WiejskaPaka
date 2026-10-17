"""Kontrola rozszerzonego testu prawdziwej przeglądarki."""
from pathlib import Path


def test_browser_smoke_checks_navigation_and_keyboard_focus():
    source = (Path(__file__).resolve().parents[1] / 'scripts' / 'check_mobile_browser.py').read_text(encoding='utf-8')
    assert "links.nth(1).click()" in source
    assert "window.location.hash" in source
    assert "document.activeElement.id" in source
    assert "links.count() == 5" in source


def test_browser_smoke_keeps_disposable_localhost_sandbox():
    source = (Path(__file__).resolve().parents[1] / 'scripts' / 'check_mobile_browser.py').read_text(encoding='utf-8')
    assert "'127.0.0.1'" in source
    assert 'demo_environment(os.environ' in source
    assert 'TemporaryDirectory(' in source
