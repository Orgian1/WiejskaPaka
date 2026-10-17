from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_financial_history_button_connected_only_to_buyer():
    source = (ROOT / 'web' / 'dashboard.js').read_text(encoding='utf-8')
    assert 'function shipmentFinancialHistoryButton(shipmentId, card)' in source
    assert "api(`/shipments/${encodeURIComponent(shipmentId)}/financial-history-test`)" in source
    assert 'c.append(shipmentFinancialHistoryButton(shipment.id,c));' in source
    assert "if(epoch!==sessionEpoch || role!=='klient')return;" in source
    assert 'data.delivery_consistent' in source
    assert 'data.refund_grosze' in source
    assert 'innerHTML' not in source[source.index('function shipmentFinancialHistoryButton'):source.index('let dashboardRequestId')]
