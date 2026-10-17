"""Kontrola rozszerzonego testu prawdziwej przeglądarki."""
from pathlib import Path


def test_browser_smoke_checks_navigation_and_keyboard_focus():
    source = (Path(__file__).resolve().parents[1] / 'scripts' / 'check_mobile_browser.py').read_text(encoding='utf-8')
    assert 'a[href="#products-section"]' in source
    assert "window.location.hash" in source
    assert "document.activeElement.id" in source
    assert 'list(EXPECTED_NAVIGATION)' in source


def test_smoke_navigation_matches_current_document():
    from html.parser import HTMLParser
    from scripts.check_mobile_browser import EXPECTED_NAVIGATION
    class Navigation(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_nav = False
            self.targets = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'nav':
                self.in_nav = 'quick-nav' in attrs.get('class', '').split()
            if tag == 'a' and self.in_nav:
                self.targets.append(attrs['href'])
        def handle_endtag(self, tag):
            if tag == 'nav':self.in_nav = False
    document = Navigation()
    document.feed((Path(__file__).resolve().parents[1] / 'web/index.html').read_text(encoding='utf-8'))
    assert document.targets == list(EXPECTED_NAVIGATION)
    assert '#nearby-section' in document.targets


def test_browser_smoke_keeps_disposable_localhost_sandbox():
    source = (Path(__file__).resolve().parents[1] / 'scripts' / 'check_mobile_browser.py').read_text(encoding='utf-8')
    assert "'127.0.0.1'" in source
    assert 'demo_environment(os.environ' in source
    assert 'TemporaryDirectory(' in source
