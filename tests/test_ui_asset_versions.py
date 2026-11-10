"""A cached old JS response must not match the URL used after deployment."""
from pathlib import Path
import re
from backend.ui_assets import versioned_index


def test_versions_change_with_content_but_not_timestamps(tmp_path):
    (tmp_path/'index.html').write_text('<script src="/assets/app.js" defer></script><link href="/assets/style.css">')
    (tmp_path/'app.js').write_text('old script')
    (tmp_path/'style.css').write_text('old style')
    first=versioned_index(tmp_path)
    assert first==versioned_index(tmp_path)
    assert '/assets/app.js?v=' in first and '/assets/style.css?v=' in first
    (tmp_path/'app.js').write_text('new script')
    second=versioned_index(tmp_path)
    assert first!=second
    assert re.search(r'href="([^"]+)"',first)[1]==re.search(r'href="([^"]+)"',second)[1]
    assert 'defer' in second


def test_all_shipped_script_and_style_urls_are_versioned():
    root=Path(__file__).resolve().parents[1]/'web'
    result=versioned_index(root)
    scripts=re.findall(r'src="(/assets/[^"]+)"',result)
    assert len(scripts)>=16
    assert all(re.fullmatch(r'/assets/[A-Za-z0-9_-]+\.js\?v=[0-9a-f]{20}',url) for url in scripts)
    assert re.search(r'href="/assets/style.css\?v=[0-9a-f]{20}"',result)
