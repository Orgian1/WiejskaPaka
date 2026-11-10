# WiejskaPaka — B/2641–B/2700: kontynuacja pełnej regresji

Uruchomiono ponownie cztery odizolowane grupy testów z opcją `--resume`.
Wszystkie testy działają na lokalnych, tymczasowych bazach SQLite; konfiguracja Neon i produkcyjne płatności nie były używane.

## Stan raportów na zakończenie sesji

- Grupa 1: 16/50 wykonanych, 16 zaliczonych.
- Grupa 2: 22/50 wykonanych, 22 zaliczone.
- Grupa 3: 16/50 wykonanych, 16 zaliczonych.
- Grupa 4: 19/50 wykonanych, 19 zaliczonych.
- Razem: **73/200 wykonanych i zaliczonych**; 127 modułów czeka na wykonanie.
- Względem poprzedniego pakietu (33/200) ukończono dodatkowych **40 modułów**.

Nie jest to ukończona pełna regresja. Testy przeglądarkowe i PostgreSQL pozostają niewykonane.

## Wznowienie

W katalogu głównym projektu uruchom kolejno:

```bash
python scripts/run_full_regression.py --shard 1/4 --resume
python scripts/run_full_regression.py --shard 2/4 --resume
python scripts/run_full_regression.py --shard 3/4 --resume
python scripts/run_full_regression.py --shard 4/4 --resume
```

Każda grupa ma oddzielny raport `full_regression_shard_N_of_4.json`. Wyniki zaliczone są wykorzystywane ponownie, o ile plik testowy nie uległ zmianie.
