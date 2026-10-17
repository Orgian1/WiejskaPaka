"""Regression for real-HTTP cross-account shipment access checks."""
from pathlib import Path


def test_http_shipment_audit_covers_both_sellers_and_stranger():
    source = (Path(__file__).resolve().parents[1] / 'scripts/check_http_multi_seller_cart.py').read_text()
    for label in (
        'seller A denied seller B shipment',
        'seller B denied seller A shipment details',
        'stranger denied seller B shipment',
        'stranger denied seller A financial history',
        'buyer can read own financial history',
        'seller A shipment list excludes seller B',
        'seller B shipment list excludes seller A',
        'buyer denied farmer shipment listing',
        'farmer denied buyer shipment listing',
    ):
        assert label in source


def test_http_shipment_audit_uses_isolated_database_and_loopback():
    source = (Path(__file__).resolve().parents[1] / 'scripts/check_http_multi_seller_cart.py').read_text()
    assert 'tempfile.TemporaryDirectory' in source
    assert 'demo_environment' in source
    assert "'127.0.0.1'" in source
    assert 'trust_env=False' in source
