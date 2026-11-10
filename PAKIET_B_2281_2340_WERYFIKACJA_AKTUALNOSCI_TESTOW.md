# WiejskaPaka B/2281–B/2340 — aktualność raportów regresji

## Problem
Raport z pozytywnym wynikiem mógł pochodzić ze starszej wersji testu. Samo porównanie nazw plików nie wykrywało zmiany treści testu po jego uruchomieniu.

## Zmiany
- `scripts/run_tests_per_file.py` zapisuje SHA-256 treści każdego uruchomionego modułu.
- `scripts/aggregate_full_regression.py` porównuje te sumy z aktualnymi plikami. Raporty stare, niepełne lub bez sumy kontrolnej są odrzucane.
- Dodano testy zmian treści testu po wygenerowaniu raportu oraz odrzucania starszego formatu.
- Uaktualniono wcześniejsze testy agregatora do nowego formatu raportu.

## Wynik lokalny
`python -m pytest -q tests/test_b2221_regression_aggregation.py tests/test_b2281_stale_regression_protection.py`: 6 passed.
`python -m compileall -q backend scripts`: OK.

## Ograniczenia
Nie uruchomiono pełnej regresji, testów PostgreSQL ani testów przeglądarkowych. Poprzednie raporty nie zawierające sum kontrolnych należy wygenerować ponownie. Brak zmian w Neon, płatnościach, domenie i hostingu.
