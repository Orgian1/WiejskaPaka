from scripts.audit_endpoint_inventory import build_report

def test_route_inventory_unique():
    rows = build_report()['routes']
    assert len(rows) > 50
    assert len({(r['method'], r['path']) for r in rows}) == len(rows)

def test_sensitive_routes_flagged_for_review():
    rows = build_report()['routes']
    assert any('orders' in r['path'] and r['sensitive_review_priority'] == 'high' for r in rows)
    assert all(not r['authorization_manually_verified'] for r in rows)

def test_release_gate_remains_closed():
    report = build_report()
    assert report['production_readiness']['production_ready'] is False
    assert report['production_readiness']['pending']
