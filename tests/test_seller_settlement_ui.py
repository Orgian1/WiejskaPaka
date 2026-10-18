from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case',['success','stale','switch_before_write','switch_after_write','already_done','invalid','unknown_response'])
def test_test_settlement_preserves_session_and_unknown_response_safety(case):
    result=subprocess.run(['node','scripts/seller_settlement_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
