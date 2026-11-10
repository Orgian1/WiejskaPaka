"""The cart quote is scoped to the selected seller and is only indicative."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_quote_display_is_accessible_and_shipment_scoped():
    html = (ROOT / 'web/index.html').read_text()
    js = (ROOT / 'web/app.js').read_text()
    assert 'id="cart-quote" role="status" aria-live="polite"' in html
    assert "cartQuoteItems.filter(item=>item.farmer_id===farmer)" in js
    assert "api('/cart/quote','POST',{items,fulfillment:quoteMode})" in js
    assert 'quote.delivery_grosze' in js
    assert 'Wycena orientacyjna' in js
    assert 'request!==cartQuoteSerial||epoch!==sessionEpoch' in js


def test_quote_refreshes_on_fulfillment_change_and_account_change():
    js = (ROOT / 'web/app.js').read_text()
    assert 'act(refreshCartQuote)}' in js
    logged = next(line for line in js.splitlines() if line.startswith("function logged(user){"))
    assert "pendingCartCheckout=null;checkoutOwner=user?.id??null;el('cart-result').textContent='';cartQuoteSerial++;cartQuoteItems=[]" in logged
    assert logged.index("resetPinRecoveryViews()") < logged.index("pendingCartCheckout=null;")
