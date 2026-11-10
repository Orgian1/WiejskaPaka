# WiejskaPaka — B/106–B/110

Poprawiono narzędzie `scripts/run_regression_chunks.py`:
- B/106: walidacja numeru partii większego od dostępnej liczby partii.
- B/107: walidacja opcji `--only-batch`.
- B/108: osobne oznaczenie niepełnego przebiegu (`complete: false`) nawet gdy wybrana partia przejdzie. Kod wyjścia 0 oznacza wtedy tylko sukces **uruchomionego podzbioru**.
- B/109: test kompletnego małego przebiegu i raportu.
- B/110: test raportowania nieudanego przebiegu.

Nowe opcje: `--list-batches` i `--only-batch N`. W celu diagnozy użyj np. `python scripts/run_regression_chunks.py --list-batches --batch-size 10` i `python scripts/run_regression_chunks.py --only-batch 4 --batch-size 10 --timeout 60`.

Weryfikacja: 15 testów narzędzia i jego zgodności wstecznej przeszło; osobno 8 testów transakcji i 44 testy web przeszły. Próba pełnej regresji trwała ponad 200 sekund i została przerwana limitem. Nie wolno uznawać jej za zaliczoną. Testy PostgreSQL/RLS na żywym serwerze pozostają niewykonane. Nie modyfikowano Neon ani płatności.
