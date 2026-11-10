from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_delivery_fields_have_accessible_names_and_autocomplete():
    js = (ROOT / 'web/app.js').read_text()
    for fragment in (
        "city.setAttribute('aria-label','Miejscowość dostawy')",
        "street.setAttribute('aria-label','Ulica i numer dostawy')",
        "postal.setAttribute('aria-label','Kod pocztowy dostawy')",
        "postal.autocomplete='postal-code'",
        "city.autocomplete='address-level2'",
        "street.autocomplete='street-address'",
        "mode.setAttribute('aria-label','Sposób realizacji zamówienia')",
    ):
        assert fragment in js


def test_pin_and_stock_inputs_have_mobile_hints():
    js = (ROOT / 'web/app.js').read_text()
    assert "qty.inputMode='numeric'" in js
    assert "pin.setAttribute('aria-label','Sześciocyfrowy PIN odbioru')" in js
    assert "pin.setAttribute('pattern','[0-9]{6}')" in js


def test_mobile_cards_prevent_wide_buttons_and_have_readable_inputs():
    css = (ROOT / 'web/style.css').read_text()
    assert '.card button{width:100%' in css
    assert '.card input,.card select{max-width:100%;font-size:16px}' in css
