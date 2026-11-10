"""Exact report amounts and authenticated downloads across account/view changes."""
from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case',['summary','maximum','wrong_month','unsafe','float','negative','boolean','wrong_type','inconsistent','missing','invalid_month','logged_out','switched_session','changed_month','http_error','wrong_format','switched_during_blob','network_error','stale_network_error','download'])
def test_admin_finance_summary_and_private_csv(case):
    result=subprocess.run(['node','scripts/admin_finance_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
