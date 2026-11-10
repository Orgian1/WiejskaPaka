"""B/111–B/115: regresja polityki długich testów przeglądarkowych."""
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_extended_browser_test_requires_opt_in():
    text=(ROOT/'tests/test_roles_offline.py').read_text(encoding='utf8')
    assert "WIEJSKAPAKA_EXTENDED_BROWSER" in text
    assert "pytest.skip(" in text

def test_extended_browser_suite_is_still_available():
    tree=ast.parse((ROOT/'scripts/check_roles_offline.py').read_text(encoding='utf8'))
    assert any(isinstance(n,ast.FunctionDef) and n.name=='run' for n in ast.walk(tree))

def test_extended_browser_covers_four_roles():
    from scripts.check_roles_offline import ROLES
    assert set(ROLES)=={'klient','rolnik','dostawca','admin'}

def test_extended_browser_covers_three_viewports():
    source=(ROOT/'scripts/check_roles_offline.py').read_text(encoding='utf8')
    assert '320, 390, 1280' in source

def test_extended_browser_is_not_a_real_http_test():
    source=(ROOT/'scripts/check_roles_offline.py').read_text(encoding='utf8')
    assert 'window.fetch = async' in source
