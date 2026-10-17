"""Shipment grouping and validation, no money transfers or external services."""
from collections import defaultdict

MAX_GROSZE = 9223372036854775807


def build_shipment_plan(lines, fulfillment):
    """Group lines by (seller, shipment key); charge each shipment exactly once.

    A shipment_key is an explicit dispatch group. If omitted, all items from
    one seller belong to one shipment. This is an indicative plan, not a booking.
    """
    if fulfillment not in ('odbior', 'dostawa'):
        raise ValueError('Nieprawidłowy sposób realizacji')
    groups = defaultdict(list)
    for line in lines:
        seller = line['farmer_id']
        product = line['product_id']
        quantity = line['quantity']
        price = line['price_grosze']
        fee = line['delivery_grosze']
        if any(type(x) is not int for x in (seller, product, quantity, price, fee)):
            raise ValueError('Nieprawidłowy typ danych')
        if seller <= 0 or product <= 0 or quantity <= 0 or price <= 0 or fee < 0:
            raise ValueError('Nieprawidłowe wartości')
        key = line.get('shipment_key', 'default')
        if not isinstance(key, str) or not key or len(key) > 64:
            raise ValueError('Nieprawidłowy identyfikator przesyłki')
        groups[(seller, key)].append(line)
    result = []
    for (seller, key), group in sorted(groups.items()):
        products = 0
        for line in group:
            amount = line['quantity'] * line['price_grosze']
            if amount > MAX_GROSZE - products:
                raise ValueError('Przekroczono limit kwoty')
            products += amount
        delivery = max(x['delivery_grosze'] for x in group) if fulfillment == 'dostawa' else 0
        if products > MAX_GROSZE - delivery:
            raise ValueError('Przekroczono limit kwoty')
        result.append({'farmer_id': seller, 'shipment_key': key,
                       'product_ids': [x['product_id'] for x in group],
                       'products_grosze': products, 'delivery_grosze': delivery,
                       'total_grosze': products + delivery})
    return result
