from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_quick_navigation_targets_exist():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert 'aria-label="Szybka nawigacja"' in html
    for target in ("auth", "products-section", "orders-section", "dashboard"):
        assert f'href="#{target}"' in html
        assert f'id="{target}"' in html

def test_mobile_navigation_is_keyboard_and_touch_friendly():
    css = (ROOT / "web/style.css").read_text(encoding="utf-8")
    assert '.quick-nav a:focus-visible' in css
    assert '.quick-nav a{display:inline-flex' in css
    assert 'min-height:44px' in css
    assert '.quick-nav{display:grid' in css
