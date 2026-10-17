"""Regresja panelu dostawcy: potwierdzenie PIN i ochrona przed dublem."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'web' / 'dashboard.js').read_text(encoding='utf-8')


def test_courier_pin_result_does_not_claim_success_on_wrong_pin():
    assert 'if(result.confirmed)' in JS
    assert 'Błędny PIN; pozostało prób:' in JS
    assert "msg('Potwierdzono odbiór całej przesyłki')" in JS


def test_courier_confirm_prevents_duplicate_request_and_clears_pin():
    assert 'if(confirmButton.disabled)return' in JS
    assert 'confirmButton.disabled=true' in JS
    assert "finally{pin.value='';confirmButton.disabled=false}" in JS
    assert 'if(!active())return' in JS
