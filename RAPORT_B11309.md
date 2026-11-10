# WiejskaPaka B/11309 — brama atomowości migracji

Cel: tani testowy VPS, docelowo 30 000 opłaconych zamówień miesięcznie.

## Zmiany
- `database/test_schema_safety.py`: konserwatywna kontrola skryptów migracyjnych przed wygenerowaniem planu jednorazowej transakcji.
- `database/test_schema_runbook.py`: wywołanie kontroli po weryfikacji sum kontrolnych.
- `tests/test_b11309_atomic_migration_gate.py`: testy blokady i odróżniania komentarzy od kodu.
- Zaktualizowano `tests/test_b11308_runbook.py`, aby nie oczekiwał błędnie gwarantowanej atomowości.

## Znaleziony problem
Istniejące pliki SQL zawierają `BEGIN` i `COMMIT`; nie wolno traktować ich jako jednego atomowego wdrożenia tylko dlatego, że uruchomiono `psql -1`. Generator obecnie odmawia stworzenia takiego planu.

## Testy
`python -m pytest -q tests/test_b1129*.py tests/test_b1130*.py`: 166 passed.

## Ograniczenia
Nie wykonano migracji na rzeczywistym PostgreSQL. Kontrola statyczna nie jest pełnym parserem SQL. Należy opracować bezpieczny wariant migracji dla pustej bazy testowej i sprawdzić go na prawdziwym PostgreSQL. Produkcyjne płatności pozostają wyłączone.
