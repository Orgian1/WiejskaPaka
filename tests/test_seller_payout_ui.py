from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case',['normal','zero','maximum','float','boolean','negative','unsafe','string','invalid_date','injected_date','mismatch','bad_commission','missing'])
def test_payout_summary_uses_exact_grosze_and_rejects_invalid_totals(case):
    result=subprocess.run(['node','scripts/seller_payout_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
