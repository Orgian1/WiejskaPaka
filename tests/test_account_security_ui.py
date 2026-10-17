from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('case',['success','duplicate','mismatch','too_short','same','account_switch','logout','error'])
def test_real_password_change_javascript(case):
    r=subprocess.run(['node','scripts/account_security_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert r.returncode==0,r.stdout+r.stderr
