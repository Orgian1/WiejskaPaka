import pytest
from backend.order_lifecycle import may_transition, require_transition, TERMINAL

@pytest.mark.parametrize('mode,old,new', [
 ('odbior','oczekuje_na_platnosc_testowa','gotowe_do_odbioru_testowo'),
 ('odbior','oczekuje_na_platnosc_testowa','anulowane_testowo'),
 ('odbior','gotowe_do_odbioru_testowo','odebrane'),
 ('dostawa','oczekuje_na_platnosc_testowa','w_drodze_testowo'),
 ('dostawa','oczekuje_na_platnosc_testowa','anulowane_testowo'),
 ('dostawa','w_drodze_testowo','odebrane'),
 ('dostawa','w_drodze_testowo','nieudana_dostawa_testowo'),
])
def test_allowed(mode,old,new):
    require_transition(mode,old,new)

@pytest.mark.parametrize('mode,old,new', [
 ('odbior','oczekuje_na_platnosc_testowa','odebrane'),
 ('dostawa','oczekuje_na_platnosc_testowa','odebrane'),
 ('odbior','gotowe_do_odbioru_testowo','nieudana_dostawa_testowo'),
 ('dostawa','w_drodze_testowo','gotowe_do_odbioru_testowo'),
 ('dostawa','odebrane','nieudana_dostawa_testowo'),
 ('odbior','anulowane_testowo','odebrane'),
 ('dostawa','nieudana_dostawa_testowo','odebrane'),
 ('unknown','oczekuje_na_platnosc_testowa','odebrane'),
])
def test_denied(mode,old,new):
    assert not may_transition(mode,old,new)
    with pytest.raises(ValueError):
        require_transition(mode,old,new)

@pytest.mark.parametrize('mode', ['odbior','dostawa'])
@pytest.mark.parametrize('terminal', sorted(TERMINAL))
def test_terminal_states_are_final(mode,terminal):
    for target in ['odebrane','anulowane_testowo','nieudana_dostawa_testowo','w_drodze_testowo']:
        assert not may_transition(mode,terminal,target)
