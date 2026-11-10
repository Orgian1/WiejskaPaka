import subprocess
from pathlib import Path


def test_delivery_views_roles_drafts_and_stale_responses():
    result = subprocess.run(['node', 'scripts/address_delivery_ui_checks.js'],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
