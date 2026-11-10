"""Read-only order integrity checks. Returns codes and identifiers, never PII."""
from backend.order_lifecycle import TRANSITIONS, TERMINAL

KNOWN_STATUSES = frozenset({state for _, state in TRANSITIONS} | set(TERMINAL))


def audit_orders(con):
    issues = []
    orders = con.execute('''SELECT o.id, o.product_id, o.farmer_id, o.quantity,
        o.subtotal_grosze, o.delivery_grosze, o.total_grosze,
        o.fulfillment, o.status, o.pin_used, o.confirmed_at,
        p.id AS existing_product, p.farmer_id AS product_farmer,
        l.order_id AS location_exists, l.pickup_point_id,
        l.delivery_city, l.delivery_street, l.delivery_postal_code
        FROM orders o LEFT JOIN products p ON p.id=o.product_id
        LEFT JOIN order_locations l ON l.order_id=o.id''').fetchall()
    for r in orders:
        oid = r['id']
        def flag(code):
            issues.append({'order_id': oid, 'code': code})
        if r['existing_product'] is None:
            flag('MISSING_PRODUCT')
        elif r['product_farmer'] != r['farmer_id']:
            flag('PRODUCT_SELLER_MISMATCH')
        money = (r['subtotal_grosze'], r['delivery_grosze'], r['total_grosze'])
        if any(type(x) is not int or x < 0 for x in money):
            flag('INVALID_ORDER_AMOUNT')
        elif money[0] + money[1] != money[2]:
            flag('ORDER_TOTAL_MISMATCH')
        if type(r['quantity']) is not int or r['quantity'] <= 0:
            flag('INVALID_QUANTITY')
        if r['fulfillment'] not in ('odbior', 'dostawa'):
            flag('UNKNOWN_FULFILLMENT')
        if r['status'] not in KNOWN_STATUSES or (r['fulfillment'], r['status']) not in TRANSITIONS and r['status'] not in TERMINAL:
            flag('UNKNOWN_ORDER_STATUS')
        if r['fulfillment'] == 'odbior' and r['status'] in ('w_drodze_testowo', 'nieudana_dostawa_testowo'):
            flag('STATUS_FULFILLMENT_MISMATCH')
        if r['fulfillment'] == 'dostawa' and r['status'] == 'gotowe_do_odbioru_testowo':
            flag('STATUS_FULFILLMENT_MISMATCH')
        if r['location_exists'] is None:
            flag('MISSING_LOCATION')
        elif r['fulfillment'] == 'odbior':
            if r['pickup_point_id'] is None or any(r[k] is not None for k in ('delivery_city', 'delivery_street', 'delivery_postal_code')):
                flag('PICKUP_LOCATION_MISMATCH')
        elif r['fulfillment'] == 'dostawa':
            if r['pickup_point_id'] is not None or any(not r[k] for k in ('delivery_city', 'delivery_street', 'delivery_postal_code')):
                flag('DELIVERY_LOCATION_MISMATCH')
        if r['status'] == 'odebrane' and (r['pin_used'] != 1 or not r['confirmed_at']):
            flag('CONFIRMATION_INCONSISTENT')
        if r['pin_used'] == 1 and r['status'] != 'odebrane':
            flag('PIN_USED_WITHOUT_RECEIPT')
        if r['confirmed_at'] and r['status'] != 'odebrane':
            flag('CONFIRMED_TIMESTAMP_WITHOUT_RECEIPT')
        if r['pin_used'] not in (0, 1):
            flag('INVALID_PIN_USED')
    stocks = con.execute('SELECT id, stock FROM products').fetchall()
    for r in stocks:
        if type(r['stock']) is not int or r['stock'] < 0:
            issues.append({'product_id': r['id'], 'code': 'INVALID_STOCK'})
    return {'checked_orders': len(orders), 'checked_products': len(stocks), 'issues': issues, 'ok': not issues}
