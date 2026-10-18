from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize('case',['normal','last','empty','cap','encoded','long_query','switch','stale','network','wrong_offset','wrong_limit','too_many','unsafe_total','float_money','boolean_stock','malformed'])
def test_bounded_catalog_page_and_request_lifecycle(case):
    result=subprocess.run(['node','scripts/catalog_page_ui_checks.js',case],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
