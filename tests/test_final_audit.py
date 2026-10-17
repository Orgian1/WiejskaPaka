import ast
from pathlib import Path
import pytest
from backend.money import split_75_20_5, full_refund
from backend.project_audit import audit_routes, audit_project

ROOT = Path(__file__).resolve().parents[1]

def test_duplicate_route_detection(tmp_path):
    f = tmp_path / "api.py"
    f.write_text("@app.get('/x')\ndef a(): pass\n@app.get('/x')\ndef b(): pass\n")
    result = audit_routes(f)
    assert len(result['duplicate_routes']) == 1
    assert result['duplicate_routes'][0]['functions'] == ['a', 'b']

def test_distinct_http_methods_not_duplicates(tmp_path):
    f = tmp_path / "api.py"
    f.write_text("@app.get('/x')\ndef a(): pass\n@app.post('/x')\ndef b(): pass\n")
    assert audit_routes(f)['duplicate_routes'] == []

def test_real_project_routes_unique():
    assert not audit_project(ROOT)['duplicate_routes']

def test_release_status_never_claims_production_ready():
    report = audit_project(ROOT)
    assert report['ready_for_production'] is False
    assert report['postgres_integration_verified'] is False
    assert report['missing_components'] == []

@pytest.mark.parametrize('amount', list(range(0, 1001)) + [10001, 999999, 10**12])
def test_financial_allocation_conserves_every_grosz(amount):
    allocations = split_75_20_5(amount)
    assert sum(allocations) == amount
    assert all(isinstance(x, int) and x >= 0 for x in allocations)
    assert all(abs(100*x - amount*w) < 100 for x,w in zip(allocations, (75,20,5)))
    assert full_refund(amount) == amount

@pytest.mark.parametrize('invalid', [-1, 1.0, True, '100', None])
def test_money_rejects_invalid_types(invalid):
    with pytest.raises(ValueError): split_75_20_5(invalid)
    with pytest.raises(ValueError): full_refund(invalid)
