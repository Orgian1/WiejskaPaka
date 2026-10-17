from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")


def test_order_button_prevents_double_submit_and_restores_after_error():
    assert "if(b.disabled)return" in JS
    assert "b.disabled=true;try{" in JS
    assert "finally{b.disabled=false}" in JS


def test_order_quantity_and_address_checked_before_request():
    assert "Number.isSafeInteger(quantity)" in JS
    assert "quantity>p.stock" in JS
    assert "postal.value.trim()" in JS
    assert "throw Error('Podaj miejscowość" in JS


def test_stale_pickup_point_request_cannot_override_delivery_mode():
    assert "const request=++pointRequest" in JS
    assert "request!==pointRequest||cardEpoch!==sessionEpoch||!box.isConnected||mode.value!=='odbior'" in JS
    assert "if(request===pointRequest&&cardEpoch===sessionEpoch&&box.isConnected&&e.message!=='SESSION_CHANGED')status.textContent=e.message" in JS
