import pytest

from backend.product_units import (
    UNITS, get_unit, line_total_grosze, package_content, quantity_atoms, quantity_text,
)


@pytest.mark.parametrize('code', list(UNITS))
def test_every_unit_has_exact_whole_quantities(code):
    atoms = quantity_atoms('2', code)
    assert quantity_text(atoms, code) == '2'
    assert line_total_grosze(201, atoms, code) == 402


@pytest.mark.parametrize('code', ['kg', 'l'])
def test_fractional_quantity_and_half_up_rounding(code):
    atoms = quantity_atoms('0,500', code)
    assert atoms == 500
    assert quantity_text(atoms, code) == '0,5'
    assert line_total_grosze(201, atoms, code) == 101
    assert line_total_grosze(200, atoms, code) == 100


@pytest.mark.parametrize('code', [c for c, u in UNITS.items() if u.scale == 1])
def test_indivisible_units_reject_fraction(code):
    with pytest.raises(ValueError):
        quantity_atoms('0.5', code)


@pytest.mark.parametrize('value', [0.5, True, None, '', 'NaN', 'Infinity', '1e3', '-1',
                                  '0', '0.0001', '1,2.3', '1000000001'])
def test_invalid_or_ambiguous_input_is_rejected(value):
    with pytest.raises(ValueError):
        quantity_atoms(value, 'kg')


def test_empty_stock_is_allowed_but_empty_order_is_not():
    assert quantity_atoms('0', 'kg', allow_zero=True) == 0
    with pytest.raises(ValueError):
        line_total_grosze(200, 0, 'kg')


def test_round_only_after_multiplication():
    # 3 grams at 500 grosze/kg is 1.5 grosze; rounding each gram loses money.
    assert line_total_grosze(500, 3, 'kg') == 2


def test_sub_grosz_line_is_not_silently_free():
    with pytest.raises(ValueError):
        line_total_grosze(1, 1, 'kg')


@pytest.mark.parametrize('code', ['ton', '', None, [], True])
def test_unknown_units_are_rejected(code):
    with pytest.raises(ValueError):
        get_unit(code)


@pytest.mark.parametrize('value', [True, 1.0, -1, 0, 100_000_001])
def test_price_must_be_bounded_integer_grosze(value):
    with pytest.raises(ValueError):
        line_total_grosze(value, 1000, 'kg')


@pytest.mark.parametrize('code', [c for c, u in UNITS.items() if u.packaged])
def test_package_requires_declared_content(code):
    with pytest.raises(ValueError):
        package_content(code)
    assert package_content(code, '250', 'g') == {'amount_atoms': 250, 'unit': 'g'}


def test_package_content_is_distinct_from_selling_quantity():
    assert package_content('opak', '10', 'szt') == {'amount_atoms': 10, 'unit': 'szt'}
    assert line_total_grosze(1500, quantity_atoms('2', 'opak'), 'opak') == 3000
    assert package_content('butelka', '0,75', 'l') == {'amount_atoms': 750, 'unit': 'l'}


def test_unpacked_product_needs_no_package_content():
    assert package_content('kg') is None


@pytest.mark.parametrize('unit', ['worek', None, [], 'kg\n'])
def test_nested_or_unknown_content_unit_rejected(unit):
    with pytest.raises(ValueError):
        package_content('worek', '15', unit)
