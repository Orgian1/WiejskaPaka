"""Offline audit of mobile HTML semantics; no network or database access."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / 'web' / 'index.html'
REQUIRED_PRIVATE = {'farmer', 'farmer-details', 'orders-section', 'dashboard', 'notifications-section', 'point-location-panel'}


class Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.anchors = []
        self.scripts = []
        self.styles = []
        self.private_visibility = {}
        self.labels = []
        self.controls = []
        self.stack = []
        self.lang = None
        self.viewport = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        ident = attrs.get('id')
        if ident:
            self.ids.append(ident)
        if tag == 'html':
            self.lang = attrs.get('lang')
        if tag == 'meta' and attrs.get('name') == 'viewport':
            self.viewport = 'width=device-width' in attrs.get('content', '')
        if tag == 'a' and attrs.get('href', '').startswith('#'):
            self.anchors.append(attrs['href'][1:])
        if tag == 'script' and attrs.get('src'):
            self.scripts.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.styles.append(attrs.get('href', ''))
        if ident in REQUIRED_PRIVATE:
            self.private_visibility[ident] = 'hidden' in attrs
        if tag == 'label':
            self.labels.append(attrs.get('for'))
        if tag in ('input', 'select', 'textarea'):
            self.controls.append((tag, ident, attrs.get('type'), bool(attrs.get('aria-label'))))


def audit_markup(html=None, assets_root=None):
    parser = Markup()
    parser.feed(HTML.read_text(encoding='utf-8') if html is None else html)
    root = ROOT / 'web' if assets_root is None else Path(assets_root)
    problems = []
    duplicates = sorted(name for name, count in Counter(parser.ids).items() if count > 1)
    if duplicates:
        problems.append('Powtórzone ID: ' + ', '.join(duplicates))
    for target in parser.anchors:
        if target and target not in parser.ids:
            problems.append('Nieistniejący cel nawigacji: #' + target)
    for section in sorted(REQUIRED_PRIVATE):
        if not parser.private_visibility.get(section):
            problems.append('Prywatna sekcja nie jest domyślnie ukryta: ' + section)
    if parser.lang != 'pl':
        problems.append('Brak polskiego języka strony')
    if not parser.viewport:
        problems.append('Brak mobilnego viewport')
    for path in parser.scripts + parser.styles:
        if not path.startswith('/assets/') or '?' in path or '#' in path:
            problems.append('Nieoczekiwany zewnętrzny zasób: ' + path)
        elif not (root / path.removeprefix('/assets/')).is_file():
            problems.append('Brak zasobu: ' + path)
    return {'ok': not problems, 'errors': problems, 'checked_ids': len(parser.ids),
            'checked_links': len(parser.anchors), 'checked_assets': len(parser.scripts) + len(parser.styles)}


if __name__ == '__main__':
    result = audit_markup()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
