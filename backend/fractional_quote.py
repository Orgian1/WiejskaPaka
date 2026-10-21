"""Read-only sale-quantity quotes; never reinterpret legacy stock or orders.

Existing stock is still counted in whole sale units. Convert it only temporarily
for comparison. A quote cannot be submitted to the integer checkout contract.
"""
from collections import Counter, defaultdict

from backend.product_units import get_unit, quantity_atoms, quantity_text, line_total_grosze
from backend.shipping_policy import shipment_fees
from backend.order_amount_limits import MAX_DB_INTEGER


class QuoteUnavailable(ValueError):
    pass


def quote_quantities(items, products, fulfillment):
    if not 1 <= len(items) <= 500:
        raise ValueError('Koszyk musi zawierać od 1 do 500 pozycji')
    ids = [item['product_id'] for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError('Połącz powtarzające się produkty w jedną pozycję')
    lines = []
    sellers = Counter()
    subtotals = defaultdict(int)
    selected = []
    for item in items:
        product = products.get(item['product_id'])
        if product is None:
            raise QuoteUnavailable('Produkt niedostępny')
        code = product['sale_unit']
        unit = get_unit(code)
        atoms = quantity_atoms(item['quantity_text'], code)
        if atoms > 1000 * unit.scale:
            raise ValueError('Maksymalna ilość to 1000 jednostek sprzedaży')
        # Never write this converted quantity back to the existing stock column.
        stock = product['stock']
        if type(stock) is not int or stock < 0:
            raise ValueError('Nieprawidłowy stan magazynowy')
        if atoms > stock * unit.scale:
            raise QuoteUnavailable('Niewystarczający stan magazynowy')
        total = line_total_grosze(product['price_grosze'], atoms, code)
        farmer = product['farmer_id']
        sellers[farmer] += 1
        if sellers[farmer] > 50:
            raise ValueError('Przesyłka jednego rolnika może zawierać maksymalnie 50 produktów')
        subtotals[farmer] += total
        selected.append(product)
        lines.append({'product_id': item['product_id'], 'name': product['name'],
                      'sale_unit': code, 'quantity_text': quantity_text(atoms, code),
                      'quantity_atoms': atoms, 'unit_scale': unit.scale,
                      'package_content': product['package_content'],
                      'unit_price_grosze': product['price_grosze'],
                      'line_total_grosze': total, 'farmer_id': farmer})
    fees = shipment_fees(selected, fulfillment)
    subtotal = sum(subtotals.values())
    delivery = sum(fees.values())
    if subtotal + delivery > MAX_DB_INTEGER:
        raise ValueError('Przekroczono limit kwoty')
    return {'contract': 'sale-quantity-quote-v1', 'items': lines,
            'subtotal_grosze': subtotal, 'delivery_grosze': delivery,
            'total_grosze': subtotal + delivery, 'currency': 'PLN',
            'indicative': True, 'checkout_supported': False,
            'inventory_reserved': False, 'payment_mode': 'test',
            'shipments': [{'farmer_id': farmer, 'items_count': sellers[farmer],
                           'subtotal_grosze': subtotals[farmer],
                           'delivery_grosze': fees[farmer],
                           'total_grosze': subtotals[farmer] + fees[farmer]}
                          for farmer in sorted(fees)],
            'notice': 'Wycena testowa ilości. Zakup ilości ułamkowych nie jest jeszcze dostępny.'}
