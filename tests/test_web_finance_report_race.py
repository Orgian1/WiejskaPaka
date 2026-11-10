from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'web' / 'dashboard.js').read_text(encoding='utf-8')


def test_farmer_payout_result_is_bound_to_latest_dashboard_refresh():
    assert "if(!active())return;box.append(dashboardCard('Rozliczenia testowe'" in JS
    assert "}catch(e){if(!active())return;box.append(node('p','Podgląd rozliczeń" in JS


def test_admin_finance_report_ignores_stale_responses():
    assert 'let financeRequestId=0;' in JS
    assert 'const financeId=++financeRequestId;' in JS
    assert 'financeId!==financeRequestId' in JS
    assert 'const selectedMonth=month.value;' in JS
    assert '(0[1-9]|1[0-2])' in JS
