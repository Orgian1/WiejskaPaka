"""Actual Uvicorn/TCP acceptance, not an in-process or browser substitute."""
from scripts.check_local_marketplace_http import run


def test_local_discovery_point_policy_checkout_and_finances_over_http():
    result=run()
    assert result['status']=='PASS'
    assert result['http_requests']>=30
    assert result['checks_count']>=120
