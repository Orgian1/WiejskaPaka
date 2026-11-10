"""Guard against cross-account checkout PIN leakage and stale delivery quotes."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text(encoding='utf-8')


def test_checkout_result_discarded_after_logout_or_account_switch():
    assert 'const checkoutEpoch=sessionEpoch;' in JS
    assert 'const checkoutAttempt=pendingCartCheckout;' in JS
    assert 'if(checkoutEpoch!==sessionEpoch || pendingCartCheckout!==checkoutAttempt)return;' in JS
    logged = next(line for line in JS.splitlines() if line.startswith("function logged(user){"))
    assert "pendingCartCheckout=null;checkoutOwner=user?.id??null;el('cart-result').textContent='';" in logged
    assert logged.index("resetPinRecoveryViews()") < logged.index("pendingCartCheckout=null;")


def test_quote_is_bound_to_selected_fulfillment():
    assert "const quoteMode=el('cart-mode').value;" in JS
    assert "{items,fulfillment:quoteMode}" in JS
    assert "quoteMode!==el('cart-mode').value" in JS
