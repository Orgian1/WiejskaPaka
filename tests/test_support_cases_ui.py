from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize('case',['draft_clear','list_switch','list_latest','detail_switch','create_switch','create_double','create_retry','history_switch','history_replaced'])
def test_support_ui_private_state_and_retries(case):
    result=subprocess.run(['node','scripts/support_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.strip()=='PASS',result.stdout+result.stderr
