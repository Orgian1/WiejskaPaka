from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] / 'web' / 'dashboard.js').read_text(encoding='utf-8')


def test_history_replaces_previous_view_instead_of_appending():
    assert "container.querySelector('[data-order-history]')" in SCRIPT
    assert 'if(existing)existing.remove()' in SCRIPT
    assert "output.dataset.orderHistory='true'" in SCRIPT
    assert 'output.replaceChildren()' in SCRIPT


def test_history_ignores_outdated_responses_and_session_changes():
    assert 'container._historyRequestId=requestId' in SCRIPT
    assert 'container._historyRequestId!==requestId' in SCRIPT
    assert 'epoch!==sessionEpoch' in SCRIPT
    assert '!container.isConnected' in SCRIPT


def test_history_failure_does_not_expose_server_errors():
    assert 'Nie udało się pobrać historii. Spróbuj ponownie.' in SCRIPT
    assert 'catch(error)' in SCRIPT
