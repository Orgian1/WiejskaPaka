"""Storage corruption and stale responses cannot release a newer intent."""
from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case',['malformed','invalid_amount','extra_fields','changed_amount','late_clear','other_active','stale_card','matching_active','invalid_reply','account_switch','withdraw_mapping'])
def test_wallet_recovery_storage_and_session_guards(case):
    result=subprocess.run(['node','scripts/wallet_recovery_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
