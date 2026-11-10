import subprocess
from pathlib import Path


def test_address_selection_and_stale_response_guards():
    result = subprocess.run(['node', 'scripts/address_search_ui_checks.js'],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
