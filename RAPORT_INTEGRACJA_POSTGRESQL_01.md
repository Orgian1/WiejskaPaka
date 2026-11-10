# WiejskaPaka — pakiet integracyjny PostgreSQL 01

## Zmiany
- Dodano `backend/postgres_test_guard.py`: ochronę przed przypadkowym uruchomieniem testów DDL na bazie produkcyjnej.
- Testy integracyjne wymagają nazwy bazy `*_test` lub `wp_test_*`.
- Połączenia zdalne wymagają jawnej zmiennej `WP_ALLOW_REMOTE_DISPOSABLE_TEST_DB=YES_I_CONFIRM` — **tylko dla odizolowanej bazy testowej**.
- Zaktualizowano konfigurację Compose, ponieważ kontener testowy łączy się z hostem `postgres` w sieci Docker.
- Dodano 9 testów ochrony konfiguracji.

## Weryfikacja
`python -m pytest -q`: **2380 passed, 4 skipped, 16 subtests passed**.
Nie wykonano testów z rzeczywistym PostgreSQL ani Neon; testy wymagające PostgreSQL zostały pominięte.

## Nadal do wykonania
1. Testy PostgreSQL na odizolowanej bazie z Docker Compose.
2. Przegląd wszystkich operacji SQL i zasad RLS, bez uruchamiania projektowanych polityk na Neon.
3. Testy pełnego cyklu zakupowego na PostgreSQL, w tym równoległych zamówień i płatności testowych.
4. Ocena bezpieczeństwa wdrożeniowego oraz prawdziwych płatności przez osobny proces.

Nie zmieniono Neon, publicznej strony ani konfiguracji płatności.
