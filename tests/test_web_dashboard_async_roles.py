from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'web' / 'dashboard.js').read_text()


def test_farmer_report_checks_session_after_success_and_failure():
    assert "if(!active())return;box.append(dashboardCard('Rozliczenia testowe'" in SOURCE
    assert "catch(e){if(!active())return;box.append(node('p','Podgląd rozliczeń" in SOURCE


def test_farmer_mutations_ignore_old_session_responses():
    assert "dispatch-test`,'POST');if(!active())return;msg(" in SOURCE
    assert "{courier_id});if(!active())return;msg(" in SOURCE


def test_admin_report_cannot_render_after_logout_and_replaces_old_report():
    assert "if(!active()||!box.isConnected||financeId!==financeRequestId)return;" in SOURCE
    assert "box.querySelectorAll('[data-test-finance-report]').forEach(n=>n.remove());" in SOURCE
    assert "report.dataset.testFinanceReport='true'" in SOURCE


def test_notification_mutation_cannot_reload_after_logout():
    assert "read`,'POST');if(epoch!==sessionEpoch)return;await loadNotifications()" in SOURCE
