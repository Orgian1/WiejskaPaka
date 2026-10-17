from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text(encoding='utf-8')


def test_farmer_profile_checks_session_before_updating_inputs():
    block = SCRIPT.split('async function loadFarmer(){', 1)[1].split('async function loadOrders()', 1)[0]
    assert "const current=()=>request===farmerRequest&&epoch===sessionEpoch&&role==='rolnik'" in block
    assert "if(!current())return;\n    el('farm-name').value" in block
    assert "if(!current())return;\n  clear('my-points')" in block


def test_farmer_profile_ignores_stale_errors_and_invalidates_on_logout():
    block = SCRIPT.split('async function loadFarmer(){', 1)[1].split('async function loadOrders()', 1)[0]
    assert "if(!current())return;\n    if(e.message==='SESSION_CHANGED')return" in block
    assert 'function logged(user){' in SCRIPT
    logged = SCRIPT.split('function logged(user){', 1)[1].split('function ', 1)[0]
    assert 'productRequest++;orderRequest++;role=user?.role||null;farmerRequest++;' in logged
    assert 'pendingCartCheckout=null' in logged


def test_farmer_profile_does_not_unnecessarily_request_product_list():
    block = SCRIPT.split('async function loadFarmer(){', 1)[1].split('async function loadOrders()', 1)[0]
    assert "api('/products/mine')" not in block
