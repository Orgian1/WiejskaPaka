from pathlib import Path


def test_admin_reconciliation_ui_wired_to_read_only_endpoints():
    source = (Path(__file__).resolve().parents[1] / 'web' / 'dashboard.js').read_text()
    assert '/admin/shipments/reconciliation?' in source
    assert '/admin/shipments/${encodeURIComponent(shipment.shipment_id)}/audit' in source
    assert 'only_issues:String(issuesOnly.checked)' in source
    assert 'id!==reconcileRequestId' in source
    assert 'card._auditRequestId!==auditId' in source
