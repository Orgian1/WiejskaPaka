import csv
import io
import pytest
from backend.finance_export import export_monthly_csv, FIELDS
from backend.platform_reports import validate_month
from tests.test_stage30 import setup


def test_csv_export_exact_amounts_and_bom():
    con = setup()
    data = export_monthly_csv(con, '2026-10')
    assert data.startswith('\ufeff')
    rows = list(csv.reader(io.StringIO(data.lstrip('\ufeff')), delimiter=';'))
    assert len(rows) == 2
    assert len(rows[0]) == len(FIELDS)
    values = dict(zip((key for key, _ in FIELDS), rows[1]))
    assert values['platform_commission_grosze'] == '50'
    assert values['gross_order_grosze'] == '1200'
    assert values['refund_event_order_count'] == '1'


@pytest.mark.parametrize('bad', ['2026-00', '2026-13', '2026-10\r\nContent-Disposition: x', '=1+1'])
def test_csv_rejects_bad_month(bad):
    with pytest.raises(ValueError):
        export_monthly_csv(setup(), bad)
