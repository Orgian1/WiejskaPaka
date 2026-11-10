"""Explicit, test-only order lifecycle policy. No payment confirmation implied."""
from typing import Final

TRANSITIONS: Final = {
    ('odbior', 'oczekuje_na_platnosc_testowa'): frozenset({'gotowe_do_odbioru_testowo', 'anulowane_testowo'}),
    ('odbior', 'gotowe_do_odbioru_testowo'): frozenset({'odebrane'}),
    ('dostawa', 'oczekuje_na_platnosc_testowa'): frozenset({'w_drodze_testowo', 'anulowane_testowo'}),
    ('dostawa', 'w_drodze_testowo'): frozenset({'odebrane', 'nieudana_dostawa_testowo'}),
}
TERMINAL: Final = frozenset({'odebrane', 'anulowane_testowo', 'nieudana_dostawa_testowo'})


def may_transition(fulfillment: str, old: str, new: str) -> bool:
    return new in TRANSITIONS.get((fulfillment, old), frozenset())


def require_transition(fulfillment: str, old: str, new: str) -> None:
    if not may_transition(fulfillment, old, new):
        raise ValueError(f'Niedozwolona zmiana statusu: {old} -> {new} ({fulfillment})')
