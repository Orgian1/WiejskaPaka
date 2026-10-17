"""End-to-end checkout on actual local TCP HTTP and disposable SQLite."""
from scripts.check_http_checkout_e2e import run


def test_http_checkout_delivery_and_refund():
    report = run()
    assert report['status'] == 'PASS'
    assert report['passed'] >= 28
    assert '100% refund including shipping' in report['checks']
    assert 'address revoked after delivery' in report['checks']


def test_http_multi_unit_delivery_fee_once():
    report = run()
    assert report['status'] == 'PASS'
    assert 'two units share one delivery fee: 698 + 501 = 1199 grosze' in report['checks']
    assert 'multi-unit amount stored in integer grosze' in report['checks']
    assert 'stranger denied multi-unit address' in report['checks']
    assert 'unassigned courier denied multi-unit address' in report['checks']
    assert 'buyer cannot dispatch multi-unit shipment' in report['checks']
