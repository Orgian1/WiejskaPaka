from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "web/app.js").read_text(encoding="utf-8")
DASH = (ROOT / "web/dashboard.js").read_text(encoding="utf-8")


def test_pickup_does_not_require_a_manual_seller_ready_button():
    assert "'Gotowe do odbioru (test)'" not in APP
    assert "'Klient sprawdził towar'" not in APP


def test_dispatch_action_prevents_double_submission():
    segment = DASH.split("'Oznacz jako wysłane (test)'", 1)[1].split("c.append(dispatch)", 1)[0]
    assert "if(dispatch.disabled)return" in segment
    assert "dispatch.disabled=true" in segment
    assert "finally{dispatch.disabled=false}" in segment
    assert "if(!active())return" in segment


def test_courier_assignment_prevents_double_submission():
    segment = DASH.split("'Przypisz dostawcę (test)'", 1)[1].split("c.append(id,assign)", 1)[0]
    assert "if(assign.disabled)return" in segment
    assert "assign.disabled=true" in segment
    assert "finally{assign.disabled=false}" in segment
    assert "if(!active())return" in segment
