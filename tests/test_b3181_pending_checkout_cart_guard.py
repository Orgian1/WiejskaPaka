from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text(encoding='utf-8')


def test_unknown_checkout_result_blocks_cart_mutations():
    assert 'function requireResolvedCheckout()' in SOURCE
    assert "addCart.onclick=()=>act(async()=>{requireResolvedCheckout();" in SOURCE
    assert "requireResolvedCheckout();const n=Number(qty.value)" in SOURCE
    assert "del.onclick=()=>act(async()=>{requireResolvedCheckout();" in SOURCE


def test_checkout_retry_keeps_same_key_until_success():
    assert "pendingCartCheckout={serialized,key:crypto.randomUUID()}" in SOURCE
    assert "'Idempotency-Key':checkoutAttempt.key" in SOURCE
    assert "pendingCartCheckout=null;clearUnresolvedCheckout();" in SOURCE
