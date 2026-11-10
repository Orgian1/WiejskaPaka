from pathlib import Path
import subprocess


def test_calendar_selection_and_account_cleanup():
    result=subprocess.run(['node','scripts/pickup_calendar_ui_checks.js'],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
