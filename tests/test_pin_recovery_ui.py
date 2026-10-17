from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('case',[
 'success','blank','duplicate','cancel','logout','role_changed','detached','hidden',
 'pagehide','stalled_timeout','password_error','invalid_pin','timeout','hide_after_reveal',
 'superseded','shipment_route','non_client',
])
def test_actual_pin_recovery_javascript(case):
    r=subprocess.run(['node','scripts/pin_recovery_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert r.returncode==0,r.stdout+r.stderr
