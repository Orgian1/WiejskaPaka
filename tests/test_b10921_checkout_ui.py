"""Parse form structure instead of asserting isolated HTML substrings."""
from html.parser import HTMLParser
from pathlib import Path


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.ancestors = {}
        self.nested_labels = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ancestors[attrs['id']] = list(self.stack)
        if tag == 'label' and any(t == 'label' for t, _ in self.stack):
            self.nested_labels.append(list(self.stack))
        if tag not in ('input', 'meta', 'link', 'br', 'img', 'hr'):
            self.stack.append((tag, attrs.get('id')))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                self.stack = self.stack[:index]
                break


def test_seller_selector_stays_available_for_delivery_and_labels_are_valid():
    html = (Path(__file__).resolve().parents[1] / 'web/index.html').read_text()
    parser = Structure()
    parser.feed(html)
    assert ('form', 'cart-checkout') in parser.ancestors['cart-farmer-select']
    assert ('div', 'cart-pickup') not in parser.ancestors['cart-farmer-select']
    assert ('div', 'cart-address') not in parser.ancestors['cart-farmer-select']
    assert not parser.nested_labels


def test_receipt_notice_does_not_require_waiving_consumer_rights():
    html = (Path(__file__).resolve().parents[1] / 'web/index.html').read_text()
    assert 'Nie ogranicza ustawowych praw konsumenta' in html
    assert 'prawakonsumenta.uokik.gov.pl/reklamacja/' in html
