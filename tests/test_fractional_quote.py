from copy import deepcopy

import pytest

from backend.fractional_quote import quote_quantities, QuoteUnavailable


def product(pid=1, **changes):
    return {'id': pid, 'name': 'Produkt', 'farmer_id': 7, 'stock': 10,
            'sale_unit': 'kg', 'package_content': None, 'price_grosze': 201,
            'delivery_grosze': 500, **changes}


def quote(amount, **changes):
    return quote_quantities([{'product_id': 1, 'quantity_text': amount}],
                            {1: product(**changes)}, 'dostawa')


@pytest.mark.parametrize('amount,total', [('0,5', 101), ('1.5', 302), ('0.005', 1), ('2', 402)])
def test_exact_rounding_after_multiplication(amount, total):
    result = quote(amount)
    assert result['subtotal_grosze'] == total
    assert result['total_grosze'] == total + 500
    assert result['checkout_supported'] is False and result['inventory_reserved'] is False


def test_litres_and_package_contents_do_not_change_the_priced_quantity():
    assert quote('1,25', sale_unit='l', price_grosze=199)['subtotal_grosze'] == 249
    packaged = quote('2', sale_unit='worek', price_grosze=1200,
                     package_content={'amount_atoms': 15000, 'unit': 'kg'})
    assert packaged['subtotal_grosze'] == 2400
    assert packaged['items'][0]['quantity_atoms'] == 2


@pytest.mark.parametrize('amount', [0.5, True, '1e2', 'NaN', '-1', '0', '0.0001', '1000.001'])
def test_bad_or_excessive_quantities_are_rejected(amount):
    with pytest.raises(ValueError):
        quote(amount)


@pytest.mark.parametrize('unit', ['szt', 'g', 'ml', 'opak', 'peczek', 'sloik', 'butelka', 'worek', 'skrzynka', 'tacka'])
def test_indivisible_units_cannot_be_fractional(unit):
    with pytest.raises(ValueError):
        quote('0.5', sale_unit=unit)


def test_zero_grosze_line_is_not_free_and_stock_is_exact():
    with pytest.raises(ValueError):
        quote('0.001', price_grosze=1)
    assert quote('2', stock=2)['subtotal_grosze'] == 402
    with pytest.raises(QuoteUnavailable):
        quote('2.001', stock=2)


def test_delivery_is_once_per_shipment_and_inputs_are_unchanged():
    products = {1: product(), 2: product(2, delivery_grosze=700),
                3: product(3, farmer_id=8, delivery_grosze=600)}
    original = deepcopy(products)
    items = [{'product_id': i, 'quantity_text': '0.5'} for i in products]
    result = quote_quantities(items, products, 'dostawa')
    assert result['delivery_grosze'] == 1300
    assert result['subtotal_grosze'] == 303
    assert [s['delivery_grosze'] for s in result['shipments']] == [700, 600]
    assert quote_quantities(items, products, 'odbior')['delivery_grosze'] == 0
    assert products == original


def test_unavailable_duplicate_and_oversized_shipment():
    item = {'product_id': 1, 'quantity_text': '1'}
    with pytest.raises(QuoteUnavailable):
        quote_quantities([item], {}, 'odbior')
    with pytest.raises(ValueError):
        quote_quantities([item, item], {1: product()}, 'odbior')
    products = {i: product(i) for i in range(1, 52)}
    with pytest.raises(ValueError):
        quote_quantities([{'product_id': i, 'quantity_text': '1'} for i in products], products, 'odbior')
