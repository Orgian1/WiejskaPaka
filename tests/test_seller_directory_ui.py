import subprocess
from pathlib import Path


def test_seller_selection_and_stale_response_isolation():
    result=subprocess.run(['node','scripts/seller_search_ui_checks.js'],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
