# WiejskaPaka B/11313 — odczytowa kontrola schematu PostgreSQL

Zmiana: `database/verify_migrated_schema.py` rozpoczyna inspekcję bazy poleceniem `SET TRANSACTION READ ONLY`, zanim wykona jakikolwiek SELECT. Ogranicza to ryzyko niezamierzonego zapisu podczas końcowego sprawdzania schematu po migracjach. Dodano test kolejności zapytań i zamknięcia połączenia.

Testy: `python -m pytest -q tests/test_b1129*.py tests/test_b1130*.py tests/test_b1131*.py` — **184 passed**.

W środowisku nie znaleziono poleceń `postgres` ani `psql`; rzeczywistej bazy PostgreSQL i migracji nie uruchomiono. Nadal wymagany jest test na instancji PostgreSQL przed wdrożeniem. Nie podłączono płatności ani VPS.
