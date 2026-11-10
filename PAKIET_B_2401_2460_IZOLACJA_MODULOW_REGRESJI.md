# WiejskaPaka B/2401–B/2460 — izolacja testów regresji

## Znaleziony i naprawiony błąd
Poprzedni skrypt `scripts/run_regression_chunks.py` uruchamiał 12 plików testowych w jednym procesie pytest i z jedną bazą SQLite. Część testów zakłada czystą bazę, więc w pakiecie 2 wystąpiły fałszywe porażki (3 błędy, 52 testy zaliczone).

## Poprawka
- Każdy plik testowy w pakiecie uruchamiany jest w osobnym procesie Python i na osobnej tymczasowej bazie SQLite.
- Raport JSON zawiera wyniki dla poszczególnych plików (`file_results`), a także dotychczasowe pola pakietu (`batch`, `returncode`, `files`).
- Po każdym pliku zapisywany jest raport częściowy, aby nie tracić diagnostyki w razie przerwania pracy.
- Środowisko potomne nadal usuwa DATABASE_URL i inne zmienne mogące wskazywać na zewnętrzną bazę danych.
- Nowy test `tests/test_b2401_regression_per_file_isolation.py` odtwarza problem i potwierdza niezależność baz.

## Faktycznie wykonane kontrole
- Pakiet regresji nr 1: PASS (12 plików; wykonany przed poprawką).
- Pakiet regresji nr 2: FAIL przed poprawką (3 niepowodzenia spowodowane współdzieleniem bazy), PASS po poprawce (12 plików w izolacji).
- Testy istniejącego mechanizmu regresji: 7 PASS.
- Nowy test izolacji: 1 PASS.
- `python -m compileall -q backend scripts`: PASS.

## Ograniczenia
Nie wykonano pełnej regresji, testów na PostgreSQL ani testów w przeglądarce. Nie podłączono płatności produkcyjnych, hostingu ani domeny; nie zmieniano Neon.
