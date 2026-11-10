"""CSV export of the internal TEST operational report; not an accounting ledger."""
import csv
import io
from backend.platform_reports import monthly_platform_report

FIELDS = (
    ('month', 'Miesiac'),
    ('report_type', 'Typ raportu'),
    ('eligible_order_count', 'Liczba zamowien kwalifikowanych'),
    ('products_grosze', 'Produkty (gr)'),
    ('delivery_grosze', 'Dostawa (gr)'),
    ('gross_order_grosze', 'Wartosc zamowien (gr)'),
    ('platform_commission_grosze', 'Prowizja platformy (gr)'),
    ('seller_due_grosze', 'Naleznosci sprzedawcow (gr)'),
    ('payment_success_event_order_count', 'Zamowienia z platnoscia testowa'),
    ('refund_event_order_count', 'Zamowienia ze zwrotem testowym'),
    ('limitations', 'Ograniczenia'),
)


def export_monthly_csv(con, month: str) -> str:
    report = monthly_platform_report(con, month)
    output = io.StringIO(newline='')
    writer = csv.writer(output, delimiter=';', lineterminator='\r\n')
    writer.writerow([label for _, label in FIELDS])
    values = []
    for key, _ in FIELDS:
        value = report[key]
        if isinstance(value, bool):
            raise ValueError('Nieoczekiwana wartosc logiczna w raporcie')
        if isinstance(value, int):
            values.append(str(value))
        else:
            value = str(value)
            # Spreadsheet formula injection protection for any future dynamic fields.
            if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
                value = "'" + value
            values.append(value)
    writer.writerow(values)
    return '\ufeff' + output.getvalue()
