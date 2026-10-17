"""Expanded local SQLite regression gate; isolated pytest process per module.

No remote database or payment connection. A missing mandatory module fails closed.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_tests_per_file import run

GROUPS = {
    'zakupy_i_magazyn': (
        'test_b1621_multiseller_shipping_regression.py',
        'test_b1681_checkout_idempotency.py',
        'test_b1801_concurrent_stock.py',
        'test_b1921_per_seller_cart_limits.py',
        'test_b401_checkout.py',
        'test_b481_multiseller_checkout.py',
        'test_b501_shared_delivery.py',
        'test_b521_shipping_policy.py',
    ),
    'dostawa_i_odbior': (
        'test_b1981_end_to_end_shipment.py',
        'test_b561_shipment_links.py',
        'test_b581_shipment_pin.py',
        'test_b621_courier_shipments.py',
        'test_b641_shipment_failure.py',
        'test_b681_shipment_details.py',
    ),
    'anulowania_i_finanse': (
        'test_b721_shipment_cancel.py',
        'test_b1321_payment_cancel_guard.py',
        'test_b1381_paid_shipment_cancel.py',
        'test_b1501_financial_history.py',
        'test_b901_reconciliation.py',
    ),
    'interfejs_i_administracja': (
        'test_b1741_checkout_ui_contract.py',
        'test_b1861_quote_ui_contract.py',
        'test_b1441_paid_cancel_panel.py',
        'test_b1561_financial_panel.py',
        'test_b741_admin_shipments.py',
    ),
}


def selected_files(root=ROOT):
    """Reject missing or duplicate test modules before any tests are executed."""
    root = Path(root)
    names = [name for group in GROUPS.values() for name in group]
    if len(names) != len(set(names)):
        raise ValueError('Duplicated module in extended gate')
    missing = [name for name in names if not (root / 'tests' / name).is_file()]
    if missing:
        raise FileNotFoundError('Missing required modules: ' + ', '.join(missing))
    return [root / 'tests' / name for name in names]


if __name__ == '__main__':
    try:
        modules = selected_files()
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    sys.exit(run(ROOT, selected=modules, timeout=90,
                 report=ROOT / 'extended_release_gate_report.json'))
