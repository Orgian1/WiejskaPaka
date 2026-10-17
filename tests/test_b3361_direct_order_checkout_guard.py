from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text(encoding='utf-8')


def test_direct_purchase_respects_pending_cart_checkout():
    # The single-item purchase button must not bypass the unresolved checkout guard.
    assert "b.onclick=()=>act(async()=>{requireResolvedCheckout();if(b.disabled)return;const orderEpoch=sessionEpoch;" in JS
    assert "const markerKey=checkoutMarkerKey();markUnresolvedCheckout();" in JS
    assert "const d=await api('/orders','POST',payload,{'Idempotency-Key':directKey});" in JS


def test_guard_applies_to_all_cart_mutations():
    assert "addCart.onclick=()=>act(async()=>{requireResolvedCheckout();" in JS
    assert "save.onclick=()=>act(async()=>{requireResolvedCheckout();" in JS
    assert "del.onclick=()=>act(async()=>{requireResolvedCheckout();" in JS


def test_direct_order_unknown_result_survives_refresh():
    # A lost response must not silently permit a second direct purchase.
    direct = JS.split("const d=await api('/orders','POST',payload,{'Idempotency-Key':directKey});")[0].split("b.onclick=()=>act(async()=>{requireResolvedCheckout();")[-1]
    assert 'markUnresolvedCheckout()' in direct
    after = JS.split("const d=await api('/orders','POST',payload,{'Idempotency-Key':directKey});")[1].split('await loadProducts()')[0]
    assert 'if(orderEpoch!==sessionEpoch)return;' in after
    assert 'sessionStorage.removeItem(markerKey)' in after
    assert 'finally{b.disabled=false}' in JS
