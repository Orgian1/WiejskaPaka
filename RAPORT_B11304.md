# WiejskaPaka B/11304 — blokada automatycznego schematu i audyt wdrożenia

## Zmiany
- `backend/test_server_preflight.py`: prywatny serwer odrzuca każdą obecność `WP_AUTO_INIT_POSTGRES` (także `0` i pustą wartość), aby schemat był przygotowany osobno przed uruchomieniem API.
- `tests/test_b11304_no_auto_schema.py`: 8 testów regresyjnych konfiguracji.

## Testy
`python -m pytest -q tests/test_b1129*.py tests/test_b1130*.py tests/test_b11289_test_server_preflight.py` — **163 passed**.

## Ważny wykryty problem wdrożeniowy
`database/postgres_schema.sql` tworzy jedynie podstawowe tabele, a kontrola uruchomienia wymaga 14 tabel (`backend/postgres_schema_preflight.py`). Dodatkowe struktury znajdują się w plikach `database/upgrade_*.sql` oraz `database/upgrade_b*.sql`; nie wolno zakładać, że samo wykonanie schematu bazowego przygotuje działającą bazę. Kolejność i kompletność migracji trzeba zweryfikować na odizolowanym PostgreSQL.

## Ograniczenia
Testy jednostkowe uruchomiono lokalnie; brak potwierdzonego testu integracyjnego na rzeczywistym PostgreSQL/VPS. Brak płatności produkcyjnych. Nie deklarujemy gotowości do uruchomienia publicznego.
