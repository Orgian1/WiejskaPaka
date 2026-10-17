"""Test-mode shipment fee policy.

One shipment = one delivery charge, irrespective of item count.
The current legacy product fee field is a *rate input*, not a per-item charge.
Until sellers can configure a shipment tariff directly, use the maximum rate
among the products in the same seller shipment. Distinct seller shipments are
charged separately. No floating-point money arithmetic.
"""
from collections import defaultdict


def shipment_fees(items, fulfillment):
    if fulfillment not in ('odbior', 'dostawa'):
        raise ValueError('Nieznany sposób realizacji')
    fees = defaultdict(int)
    for item in items:
        seller = int(item['farmer_id'])
        fee = item['delivery_grosze']
        if type(fee) is not int or fee < 0:
            raise ValueError('Nieprawidłowa opłata za przesyłkę')
        fees[seller] = max(fees[seller], fee)
    if fulfillment == 'dostawa' and any(fee == 0 for fee in fees.values()):
        raise ValueError('Sprzedawca musi ustalić dodatnią opłatę za dostawę na adres')
    return {seller: (fee if fulfillment == 'dostawa' else 0)
            for seller, fee in fees.items()}
