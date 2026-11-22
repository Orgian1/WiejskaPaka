"""Publish the demo notices when the operator has supplied the deployment details."""
from html import escape
import os
from pathlib import Path
from string import Template


DOCUMENTS = {
    'regulamin': 'Regulamin demo',
    'prywatnosc': 'Prywatność i pamięć przeglądarki',
}
TEMPLATE_DIR = Path(__file__).with_name('demo_legal_templates')


def legal_details():
    details = {
        'address': os.environ.get('WP_DEMO_OPERATOR_ADDRESS', '').strip(),
        'effective_date': os.environ.get('WP_DEMO_LEGAL_DATE', '').strip(),
        'retention': os.environ.get('WP_DEMO_DATA_RETENTION', '').strip(),
        'providers': os.environ.get('WP_DEMO_DATA_PROVIDERS', '').strip(),
    }
    return details if all(details.values()) else None


def render_document(name, details):
    title = DOCUMENTS[name]
    template = Template((TEMPLATE_DIR / f'{name}.html').read_text(encoding='utf-8'))
    body = template.substitute({key: escape(value) for key, value in details.items()})
    return f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{title} — WiejskaPaka</title><link rel="stylesheet" href="/assets/style.css">
</head><body><header><h1>{title}</h1><p>WiejskaPaka · środowisko testowe</p></header>
<main><section class="wide-section">{body}
<p><a href="/">Wróć do WiejskiejPaki</a></p></section></main></body></html>'''


def add_legal_links(html):
    links = '<a href="/regulamin">Regulamin demo</a> · <a href="/prywatnosc">Prywatność i pamięć przeglądarki</a>'
    return html.replace('<!-- demo-legal-registration -->', f'<p class="muted">{links}</p>').replace(
        '<!-- demo-legal-footer -->', f'<nav aria-label="Informacje prawne">{links}</nav>'
    )
