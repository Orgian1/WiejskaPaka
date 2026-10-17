from pathlib import Path


def test_panel_exposes_separate_cancel_flows_and_explicit_test_refund():
    script = (Path(__file__).resolve().parents[1] / 'web' / 'dashboard.js').read_text()
    assert 'Anuluj nieopłaconą przesyłkę (test)' in script
    assert 'Anuluj opłaconą przesyłkę i zwróć kwotę (TEST)' in script
    assert '/cancel-paid-test' in script
    assert 'result.already_processed' in script
    assert 'Nie przelano prawdziwych pieniędzy' in script
