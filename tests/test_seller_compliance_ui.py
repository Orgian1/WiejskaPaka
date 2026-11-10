from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case',['success','duplicate','anonymous','buyer','switch','logout','error','invalid','ack_error','ack_switch'])
def test_actual_seller_compliance_javascript(case):
    result=subprocess.run(['node','scripts/seller_compliance_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
