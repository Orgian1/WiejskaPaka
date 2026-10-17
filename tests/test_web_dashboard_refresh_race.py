from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'web' / 'dashboard.js').read_text(encoding='utf-8')


def test_dashboard_refresh_has_request_generation_guard():
    assert 'let dashboardRequestId=0;' in JS
    assert 'const requestId=++dashboardRequestId;' in JS
    assert 'requestId===dashboardRequestId' in JS
    assert 'if(!active())return;' in JS
    assert 'if(active())await loadNotifications();' in JS


def test_notifications_refresh_ignores_older_results():
    assert 'let notificationsRequestId=0;' in JS
    assert 'const requestId=++notificationsRequestId;' in JS
    assert 'requestId!==notificationsRequestId)return;' in JS
