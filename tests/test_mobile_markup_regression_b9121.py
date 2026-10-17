"""Regresja struktury mobilnej: testy offline, bez bazy i sieci."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_mobile_markup import audit_markup


def test_current_mobile_markup_passes():
    result = audit_markup()
    assert result['ok'], result['errors']
    assert result['checked_ids'] > 0
    assert result['checked_assets'] > 0


def test_duplicate_id_is_detected():
    html = '<html lang="pl"><meta name="viewport" content="width=device-width"><div id="x"></div><div id="x"></div>'
    result = audit_markup(html)
    assert not result['ok']
    assert any('Powtórzone ID' in err for err in result['errors'])


def test_missing_anchor_target_is_detected():
    html = '<html lang="pl"><meta name="viewport" content="width=device-width"><a href="#missing">go</a>'
    result = audit_markup(html)
    assert not result['ok']
    assert any('Nieistniejący cel' in err for err in result['errors'])


def test_external_asset_is_detected():
    html = '<html lang="pl"><meta name="viewport" content="width=device-width"><script src="https://example.org/a.js"></script>'
    result = audit_markup(html)
    assert not result['ok']
    assert any('Nieoczekiwany zewnętrzny zasób' in err for err in result['errors'])


def test_missing_viewport_is_detected():
    html = '<html lang="pl"></html>'
    result = audit_markup(html)
    assert not result['ok']
    assert 'Brak mobilnego viewport' in result['errors']
