"""Execute actual account transition code with stale private DOM and no network result."""
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('case',['logout','switch_client','switch_farmer','switch_courier','switch_admin','offline_logout','repeat_reset'])
def test_account_transition_clears_drafts_and_detached_private_nodes(case):
    run=subprocess.run(['node','scripts/account_view_privacy_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert run.returncode==0,run.stdout+run.stderr
