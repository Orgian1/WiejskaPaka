from pathlib import Path


def test_cart_checkout_uses_replay_key_and_shipment_pin():
    js = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text()
    assert "'Idempotency-Key':checkoutAttempt.key" in js
    assert 'crypto.randomUUID()' in js
    assert 'pendingCartCheckout.serialized!==serialized' in js
    assert 'pendingCartCheckout=null;clearUnresolvedCheckout();' in js
    assert "checkoutPinLabel(result,'shipment_pin_test_only')" in js
    assert 'result.orders.map(o=>o.pickup_code' not in js
    logged = next(line for line in js.splitlines() if line.startswith("function logged(user){"))
    assert 'pendingCartCheckout=null;' in logged
    assert logged.index("resetPinRecoveryViews()") < logged.index("pendingCartCheckout=null;")
