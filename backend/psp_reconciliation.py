"""Read-only reconciliation of TEST payment records against manually supplied PSP-like entries.

No external calls, no real provider integration and no bank transfers.
"""
from collections import Counter

MAX_ROWS = 500


def reconcile_test_payments(con, entries):
    if not isinstance(entries, list) or len(entries) > MAX_ROWS:
        raise ValueError('Wymagana lista maksymalnie 500 pozycji')
    seen = set()
    normalized = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict) or set(item) != {'order_id', 'amount_grosze', 'status'}:
            raise ValueError(f'Nieprawidłowe pola pozycji {index + 1}')
        order_id, amount, status = item['order_id'], item['amount_grosze'], item['status']
        if type(order_id) is not int or order_id <= 0 or type(amount) is not int or amount < 0:
            raise ValueError(f'Nieprawidłowe kwoty lub ID w pozycji {index + 1}')
        if status not in ('paid', 'refunded', 'pending'):
            raise ValueError(f'Nieznany status pozycji {index + 1}')
        if order_id in seen:
            raise ValueError(f'Powtórzony identyfikator zamówienia {order_id}')
        seen.add(order_id)
        normalized.append((order_id, amount, status))
    results = []
    counts = Counter()
    for order_id, amount, external_status in normalized:
        row = con.execute('SELECT total_grosze,refund_grosze,state FROM payment_simulations WHERE order_id=?', (order_id,)).fetchone()
        if row is None:
            outcome, reasons = 'unknown_order', ['Nie znaleziono zamówienia w symulacji']
        else:
            local = dict(row)
            reasons = []
            if local['total_grosze'] != amount:
                reasons.append('Niezgodna kwota brutto')
            state = local['state']
            expected = {'awaiting_payment': 'pending', 'pending_test': 'pending', 'failed_test': 'pending',
                        'paid_test': 'paid', 'completed_test': 'paid',
                        'paid_out_test': 'paid', 'refunded_test': 'refunded'}.get(state)
            if expected is None:
                reasons.append('Nieznany lokalny stan płatności')
            if state == 'refunded_test' and local['refund_grosze'] != local['total_grosze']:
                reasons.append('Niepełna kwota zwrotu')
            if external_status != expected:
                reasons.append('Niezgodny status płatności')
            outcome = 'matched' if not reasons else 'mismatch'
        counts[outcome] += 1
        results.append({'order_id': order_id, 'outcome': outcome, 'reasons': reasons})
    return {'mode': 'offline_test_read_only', 'checked': len(results),
            'matched': counts['matched'], 'mismatched': counts['mismatch'],
            'unknown_orders': counts['unknown_order'], 'items': results,
            'warning': 'Porównanie z danymi ręcznie wprowadzonymi; brak połączenia z operatorem płatności.'}
