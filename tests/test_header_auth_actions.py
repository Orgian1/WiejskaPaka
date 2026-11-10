"""Kontrakt publicznych akcji konta w nagłówku WiejskaPaka."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HeaderLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_header = False
        self.links = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "header":
            self.in_header = True
        if self.in_header and tag == "a" and attributes.get("id", "").startswith("header-"):
            self.links[attributes["id"]] = attributes

    def handle_endtag(self, tag):
        if tag == "header":
            self.in_header = False


def test_public_header_has_login_and_registration_links():
    parser = HeaderLinks()
    parser.feed((ROOT / "web/index.html").read_text(encoding="utf-8"))
    assert parser.links["header-login-link"]["href"] == "#auth"
    assert parser.links["header-register-link"]["href"] == "#role"
    assert parser.links["header-panel-link"]["href"] == "#account-section"
    assert "hidden" in parser.links["header-panel-link"]


def test_session_transition_switches_header_actions():
    source = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert "el('header-login-link').hidden=!!user" in source
    assert "el('header-register-link').hidden=!!user" in source
    assert "el('header-panel-link').hidden=!user" in source


def test_header_actions_remain_responsive():
    css = (ROOT / "web/style.css").read_text(encoding="utf-8")
    assert ".header-auth-actions" in css
    assert "@media(max-width:850px)" in css


def test_header_account_actions_have_unique_ids_and_existing_targets():
    """Links must point to real elements; duplicate IDs make JS toggling ambiguous."""
    from collections import Counter

    class Document(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = []

        def handle_starttag(self, tag, attrs):
            element_id = dict(attrs).get("id")
            if element_id:
                self.ids.append(element_id)

    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    document = Document()
    document.feed(html)
    counts = Counter(document.ids)
    assert all(count == 1 for count in counts.values()), [key for key, count in counts.items() if count != 1]

    header = HeaderLinks()
    header.feed(html)
    expected = {"header-login-link", "header-register-link", "header-panel-link"}
    assert expected <= header.links.keys()
    for action in expected:
        href = header.links[action]["href"]
        assert href.startswith("#") and href[1:] in counts
