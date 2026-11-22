import pytest

from tests import test_purchase_record_http_restart as http_fixture
from tests.test_sample_demo_browser import sample_browser_server


@pytest.fixture
def legal_server(tmp_path, monkeypatch):
    demo_environment = http_fixture.demo_environment

    def configured_environment(source, database):
        return {
            **demo_environment(source, database),
            'WP_DEMO_OPERATOR_ADDRESS': 'Testowa 12 <test>',
            'WP_DEMO_LEGAL_DATE': '23.11.2026',
            'WP_DEMO_DATA_RETENTION': 'Retencja skonfigurowana na potrzeby testu.',
            'WP_DEMO_DATA_PROVIDERS': 'Dostawcy ustawieni na potrzeby testu.',
        }

    monkeypatch.setattr(http_fixture, 'demo_environment', configured_environment)
    with http_fixture.server(tmp_path / 'legal.sqlite3') as client:
        yield client


def test_public_documents_and_server_count(legal_server):
    page = legal_server.get('/')
    robots_directive = '<meta name="robots" content="noindex">'
    assert robots_directive not in page.text
    for name in ('regulamin', 'prywatnosc'):
        assert page.text.count(f'href="/{name}"') == 2
        document = legal_server.get('/' + name)
        assert document.status_code == 200
        assert robots_directive in document.text
        assert 'Testowa 12 &lt;test&gt;' in document.text
        assert 'Testowa 12 <test>' not in document.text
        if name == 'prywatnosc':
            assert 'netcup GmbH' in document.text

    for role in ('klient', 'rolnik'):
        body = {'role': role, 'email': f'{role}@example.invalid', 'password': 'Test-only-legal-demo-123!'}
        assert legal_server.post('/auth/register', json=body).status_code == 201
        shown = [legal_server.post('/auth/login', json=body).json()['show_login_guide'] for _ in range(6)]
        assert shown == [True] * 5 + [False]


def test_browser_does_not_store_guide_count(sample_browser_server, legal_server):
    browser, _, _ = sample_browser_server
    body = {'role': 'klient', 'email': 'browser@example.invalid', 'password': 'Test-only-legal-demo-123!'}
    assert legal_server.post('/auth/register', json=body).status_code == 201
    page = browser.new_page(viewport={'width': 390, 'height': 844})
    try:
        page.goto(str(legal_server.base_url))
        page.locator('#account-nav-link').click()
        page.locator('#auth a[href="/regulamin"]').click()
        assert page.get_by_role('heading', name='Regulamin demo').is_visible()
        page.get_by_role('link', name='Wróć do WiejskiejPaki').click()
        page.locator('#account-nav-link').click()
        page.locator('#email').fill(body['email'])
        page.locator('#password').fill(body['password'])
        page.locator('#auth button[type=submit]').click()
        page.locator('#login-guide[open]').wait_for()
        assert page.evaluate('localStorage.length') == 0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    finally:
        page.close()
