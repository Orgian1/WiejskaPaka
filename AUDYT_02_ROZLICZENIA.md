# WiejskaPaka — audyt 02: integralność kwot i zwrotów

## Wykonane zmiany
- `backend/payment_simulator.py`: przed każdą zmianą stanu, włącznie z ponowionym zdarzeniem, sprawdzane są typy kwot (wyłącznie `int`, nie `bool`), brak kwot ujemnych, suma produktów i dostawy, suma prowizji i należności sprzedawcy, limity zwrotu i wypłaty.
- `tests/test_payment_invariants_audit02.py`: test zachowania sumy podziału 75/20/5 dla 0–1000 groszy, odrzucanie uszkodzonych kwot, pełny zwrot za niedostarczenie z winy kuriera i blokada wypłaty po zwrocie.

## Testy lokalne
`python -m pytest -q`: **2363 passed, 4 skipped, 16 subtests passed**. Testy działają lokalnie, nie są dowodem poprawności integracji z Neon.

## Ograniczenia / blokady produkcyjne
- Symulator nie jest operatorem płatności; nie realizuje przelewów ani faktycznych zwrotów.
- Trwała idempotencja i niezmienność zdarzeń wymagają transakcyjnego zapisu w PostgreSQL, unikalnych identyfikatorów i testów równoległych żądań.
- RLS nadal wyłączony. Brak testów rzeczywistego połączenia z Neon.
- Nie zmieniano strony publicznej ani konfiguracji płatności.
