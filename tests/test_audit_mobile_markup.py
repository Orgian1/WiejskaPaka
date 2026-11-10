from scripts.audit_mobile_markup import audit_markup, HTML


def test_current_mobile_markup_audit_passes():
    result = audit_markup()
    assert result['ok'], result['errors']
    assert result['checked_links'] >= 4
    assert result['checked_assets'] >= 3


def test_audit_detects_missing_navigation_target():
    html = HTML.read_text(encoding='utf-8').replace('href="#dashboard"', 'href="#not-present"')
    assert any('Nieistniejący cel' in error for error in audit_markup(html)['errors'])


def test_audit_detects_exposed_private_panel():
    html = HTML.read_text(encoding='utf-8').replace('id="dashboard" hidden', 'id="dashboard"')
    assert any('dashboard' in error for error in audit_markup(html)['errors'])


def test_audit_detects_duplicate_ids():
    html = HTML.read_text(encoding='utf-8').replace('id="notice"', 'id="auth"')
    assert any('Powtórzone ID' in error for error in audit_markup(html)['errors'])
