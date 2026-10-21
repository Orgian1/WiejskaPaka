from pathlib import Path
import subprocess


def test_same_package_checkout_and_account_isolation():
    result=subprocess.run(['node','scripts/same_package_ui_checks.js'],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
