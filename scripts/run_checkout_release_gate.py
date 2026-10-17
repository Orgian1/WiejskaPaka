"""Local checkout release gate. Each test file runs in a separate process/database.

Run: python scripts/run_checkout_release_gate.py
No PostgreSQL connection or live payment provider is used.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_tests_per_file import run

CRITICAL_MODULES = (
    'test_b1621_multiseller_shipping_regression.py',
    'test_b1681_checkout_idempotency.py',
    'test_b1741_checkout_ui_contract.py',
    'test_b1801_concurrent_stock.py',
    'test_b1861_quote_ui_contract.py',
    'test_b1921_per_seller_cart_limits.py',
    'test_b1981_end_to_end_shipment.py',
    'test_b581_shipment_pin.py',
    'test_b641_shipment_failure.py',
    'test_b721_shipment_cancel.py',
)

if __name__ == '__main__':
    missing = [name for name in CRITICAL_MODULES if not (ROOT / 'tests' / name).is_file()]
    if missing:
        print('Missing required tests: ' + ', '.join(missing), file=sys.stderr)
        sys.exit(2)
    sys.exit(run(ROOT, selected=[ROOT / 'tests' / name for name in CRITICAL_MODULES],
                 timeout=90, report=ROOT / 'checkout_release_gate_report.json'))
