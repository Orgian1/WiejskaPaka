from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_async_reads_guard_session_epoch():
    source = (ROOT / 'web/dashboard.js').read_text()
    assert 'const epoch=sessionEpoch;' in source
    assert 'if(epoch!==sessionEpoch)return;' in source
    assert 'if(epoch!==sessionEpoch||!container.isConnected)return;' in source
    assert 'if(active())await loadNotifications();' in source


def test_courier_confirm_only_while_dispatched():
    source = (ROOT / 'web/dashboard.js').read_text()
    assert "if(shipment.status==='w_drodze_testowo')" in source
    assert "if(!/^\\d{6}$/.test(pin.value))" in source


def test_farmer_pin_validation_before_request():
    source = (ROOT / 'web/app.js').read_text()
    assert "if(!/^\\d{6}$/.test(pin.value))throw Error('PIN musi mieć 6 cyfr')" in source
    assert "if(!checked.checked)throw Error('Najpierw klient musi sprawdzić produkty')" in source
    assert "b.disabled=true;let d;try{d=await api(`/orders/${o.id}/confirm`" in source
