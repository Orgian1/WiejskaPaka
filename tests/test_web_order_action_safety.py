from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text(encoding='utf-8')


def test_cancel_button_blocks_repeated_requests_and_recovers_on_failure():
    assert "if(b.disabled)return;b.disabled=true;try{await api(`/orders/${o.id}/cancel-test`" in SOURCE
    assert "await loadProducts()}finally{b.disabled=false}" in SOURCE


def test_pickup_pin_is_cleared_even_if_server_request_fails():
    assert "await api(`/orders/${o.id}/confirm`" in SOURCE
    assert "finally{pin.value='';b.disabled=false}" in SOURCE
