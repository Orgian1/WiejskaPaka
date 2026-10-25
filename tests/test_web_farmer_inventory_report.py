from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "web" / "dashboard.js").read_text(encoding="utf-8")


def test_farmer_dashboard_displays_inventory_and_stock():
    assert "Moje produkty i stany magazynowe" in JS
    assert "for(const product of products)" in JS
    assert "Number.isSafeInteger(stock)&&stock>=0" in JS
    assert "Dostępne w magazynie: ${availability}" in JS
    assert "Cena: ${money(product.price_grosze)}" in JS


def test_admin_report_is_readable_and_replaces_previous_report():
    assert "Raport testowy — dane symulacyjne" in JS
    assert "adminFinanceSummaryLines(r,selectedMonth)" in JS
    assert "dashboardCard('Raport testowy — dane symulacyjne',lines)" in JS
    assert "querySelectorAll('[data-test-finance-report]').forEach(n=>n.remove())" in JS
