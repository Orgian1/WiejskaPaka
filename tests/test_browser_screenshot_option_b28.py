"""Kontrakt opcjonalnych zrzutów testu mobilnego (bez sesji użytkownika)."""
import ast
from pathlib import Path
from scripts import check_mobile_browser as runner


def test_browser_runner_accepts_optional_screenshot_directory():
    assert runner.check_browser.__defaults__ == (None,)
    source = Path(runner.__file__).read_text(encoding='utf-8')
    ast.parse(source)
    assert "parser.add_argument('--screenshots'" in source
    assert "page.screenshot(path=" in source
    assert 'if screenshot_dir is not None:' in source


def test_browser_screenshots_are_taken_only_from_public_page():
    source = Path(runner.__file__).read_text(encoding='utf-8')
    assert "page.goto(address, wait_until='networkidle')" in source
    assert 'page.screenshot(' in source
    assert source.index("page.goto(address, wait_until='networkidle')") < source.index('page.screenshot(')
    assert 'login(' not in source
    assert "wiejskapaka_public_{width}x{height}.png" in source
