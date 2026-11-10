"""Regression checks for the anonymous HTTP route audit."""
from scripts.audit_anonymous_http_routes import resolved_path
from scripts.audit_route_auth_dependencies import audit, is_public


def test_all_nonpublic_routes_have_direct_auth_dependency():
    rows = [r for r in audit()['routes'] if not is_public(r['method'], r['path'])]
    assert rows
    assert all('current_user' in r['dependencies'] for r in rows)


def test_all_dynamic_paths_are_resolved():
    for row in audit()['routes']:
        path = resolved_path(row['path'])
        assert '{' not in path and '}' not in path
        assert path.startswith('/')


def test_public_catalog_not_in_private_audit():
    assert is_public('GET', '/products')
    assert not is_public('POST', '/products')
    assert not is_public('GET', '/orders/me')
