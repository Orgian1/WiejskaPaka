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
