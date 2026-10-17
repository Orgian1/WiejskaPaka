from scripts.audit_route_auth_dependencies import audit

def test_inventory_covers_all_routes():
    result = audit()
    assert result['total'] >= 87
    assert all(row['manual_review_required'] for row in result['routes'])

def test_sensitive_endpoints_have_auth_dependency():
    result = audit()
    assert not [r for r in result['routes'] if r['review_flag'] == 'NO_DIRECT_AUTH_DEPENDENCY'], 'Review unauthenticated route(s)'

def test_inventory_does_not_claim_authorization_verified():
    result = audit()
    assert 'not determined' in result['scope']


def test_recovery_exceptions_are_exact_methods_and_paths():
    from scripts.audit_route_auth_dependencies import is_public, RECOVERY_ROUTES
    rows = [row for row in audit()['routes'] if row['review_flag']=='RECOVERY_TOKEN_FLOW']
    assert {(row['method'],row['path']) for row in rows} == RECOVERY_ROUTES
    assert all(row['manual_review_required'] for row in rows)
    assert not is_public('POST','/auth/password-reset-test/options')
    assert not is_public('GET','/auth/password-reset-test/confirm')
    assert not is_public('POST','/auth/password-reset-test/future-handler')
