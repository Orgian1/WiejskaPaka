from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case',['success','non_admin','stale_read','read_error','pagination','short','stale_write','write_error'])
def test_actual_admin_review_javascript(case):
    result=subprocess.run(['node','scripts/admin_seller_review_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
