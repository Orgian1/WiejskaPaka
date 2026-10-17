from pathlib import Path
import subprocess
import pytest


@pytest.mark.parametrize('case', ['success','request','mismatch','network','duplicate','account_switch','disabled'])
def test_actual_reset_javascript(case):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(['node','scripts/password_reset_ui_checks.js',case],cwd=root,
                            capture_output=True,text=True,timeout=10)
    assert result.returncode == 0, result.stdout+result.stderr
