"""Reproducible financial property audit, separate from pytest case counts."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.invoicing import calculate_commission_grosze
from backend.settlement_preview import calculate
from backend.money import split_75_20_5
from backend.payment_simulator import new_payment, apply_event


def run():
    rng = random.Random(1092111280)
    checks = 0
    samples = list(range(10001)) + [rng.randrange(0, 9_000_000_000_000) for _ in range(10000)]
    for amount in samples:
        rate = rng.choice([0, 1, 50, 499, 500, 501, 2300, 9999, 10000])
        got = calculate_commission_grosze(amount, rate)
        expected = int((Decimal(amount) * Decimal(rate) / Decimal(10000)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        assert got == expected
        checks += 1
        parts = split_75_20_5(amount)
        assert sum(parts) == amount and all(type(v) is int and v >= 0 for v in parts)
        checks += 1
        if amount > 0:
            shipping = rng.randrange(0, min(100001, 9_000_000_000_000 - amount + 1))
            summary = calculate(amount, shipping, rate)
            assert summary['commission_grosze'] + summary['seller_amount_grosze'] == amount + shipping
            checks += 1
            paid = apply_event(new_payment(1, amount, shipping, rate), 'paid', 'payment_success_test')
            refund = apply_event(paid, 'refund', 'delivery_failed_by_courier_test')
            assert refund.refund_grosze == amount + shipping and refund.payout_grosze == 0
            checks += 1
            payout = apply_event(apply_event(paid, 'complete', 'order_completed_test'), 'weekly', 'weekly_payout_test')
            assert payout.payout_grosze + payout.commission_grosze == payout.total_grosze and payout.refund_grosze == 0
            checks += 1
    return {'status': 'PASS', 'seed': 1092111280, 'sampled_amounts': len(samples), 'invariant_checks': checks,
            'scope': 'integer grosze commission vs independent Decimal oracle; 75/20/5, conservation, full refund, payout',
            'timestamp_utc': datetime.now(timezone.utc).isoformat()}


if __name__ == '__main__':
    report = run()
    (ROOT / 'audit_money_properties.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
