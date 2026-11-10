"""Statyczny kontrakt HTML uruchamianego UI (nie prototypu marketingowego)."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.assets = []
        self.hidden = set()
        self.forms = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
            if 'hidden' in a:
                self.hidden.add(a['id'])
            if tag == 'form':
                self.forms.add(a['id'])
        if tag == 'a' and a.get('href', '').startswith('#'):
            self.links.append(a['href'][1:])
        if tag == 'script' and 'src' in a:
            self.assets.append(a['src'])
        if tag == 'link' and a.get('rel') == 'stylesheet':
            self.assets.append(a.get('href', ''))


def parse_ui():
    doc = Markup()
    doc.feed((ROOT / 'web' / 'index.html').read_text(encoding='utf-8'))
    return doc


def test_ui_has_unique_ids_and_working_navigation_targets():
    doc = parse_ui()
    assert len(doc.ids) == len(set(doc.ids)), 'Powtórzone identyfikatory HTML'
    assert doc.links, 'Brak nawigacji'
    assert all(fragment in doc.ids for fragment in doc.links), 'Odnośnik do nieistniejącej sekcji'


def test_private_panels_hidden_before_login():
    doc = parse_ui()
    assert {'farmer', 'farmer-details', 'orders-section', 'dashboard',
            'notifications-section'} <= doc.hidden
    assert {'auth', 'new-product', 'profile-form', 'point-form'} <= doc.forms


def test_local_ui_assets_exist():
    doc = parse_ui()
    assert {'/assets/app.js', '/assets/dashboard.js', '/assets/style.css'} <= set(doc.assets)
    for asset in doc.assets:
        assert asset.startswith('/assets/') and '..' not in asset
        assert (ROOT / 'web' / asset.removeprefix('/assets/')).is_file(), asset
