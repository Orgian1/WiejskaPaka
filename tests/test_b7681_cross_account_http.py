"""End-to-end HTTP authorization regression for six independent accounts."""
from scripts.audit_cross_account_http import run

def test_cross_account_idor_real_http():
    report=run()
    assert report['status']=='PASS'
    assert report['count']>=40
