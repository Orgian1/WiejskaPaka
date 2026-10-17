"""Actual TCP HTTP integration; no in-process client substitution."""
from scripts.check_purchase_records_http import run

def test_original_terms_over_actual_http():
    result=run()
    assert result['status']=='PASS'
    assert result['http_requests']>=50
    assert result['checks_count']>=150
