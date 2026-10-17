from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('case',['refresh','others','all','duplicate','anonymous','account_switch','all_switch','logout','new_request','error','invalid'])
def test_real_session_controls_javascript(case):
    r=subprocess.run(['node','scripts/session_security_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert r.returncode==0,r.stdout+r.stderr
