"""Browser regression checks run with Node.js when available; no network needed."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_browser_js_syntax():
    if not shutil.which('node'):
        pytest.skip('Node.js not installed')
    for name in ('app.js', 'dashboard.js'):
        subprocess.run(['node', '--check', str(ROOT / 'web' / name)], check=True, capture_output=True)


def test_logout_invalidates_pending_requests_and_clears_private_views():
    source = (ROOT / 'web' / 'app.js').read_text(encoding='utf-8')
    assert 'if(epoch!==sessionEpoch)' in source
    assert 'sessionEpoch++;token=null;logged(null)' in source
    for section in ('orders', 'my-points', 'dashboard-content', 'notifications-list'):
        assert section in source
    assert "for(const id of ['cart-checkout','profile-form','point-form','new-product'])el(id).reset()" in source
    logged=next(line for line in source.splitlines() if line.startswith('function logged(user){'))
    assert 'clearPrivateAccountViews();' in logged
