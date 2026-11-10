from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'web' / 'app.js').read_text()


def test_unresolved_marker_persists_without_personal_information():
    assert "sessionStorage.setItem(key,'1')" in JS
    assert "sessionStorage.getItem(key)==='1'" in JS
    assert 'checkoutOwner=user?.id??null' in JS
    assert "sessionStorage.setItem(key,JSON.stringify(payload))" not in JS
    assert 'markUnresolvedCheckout();' in JS
    assert 'pendingCartCheckout=null;clearUnresolvedCheckout();' in JS


def test_refresh_requires_explicit_history_review():
    assert 'if(hasUnresolvedCheckout()&&!pendingCartCheckout)' in JS
    assert 'Sprawdziłem historię — odblokuj koszyk' in JS
    assert 'clearUnresolvedCheckout();pendingCartCheckout=null;' in JS
    assert 'el(\'cart-submit\').disabled=!farmers.size||hasUnresolvedCheckout()' in JS
