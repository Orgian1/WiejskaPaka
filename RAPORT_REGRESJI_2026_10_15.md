# WiejskaPaka — próba pełnej regresji

Uruchomiono cztery niezależne grupy, po 50 modułów każda (200 modułów łącznie w planie). Każdy moduł otrzymuje osobny proces i tymczasową bazę SQLite. Wykonanie zostało przerwane limitem czasu środowiska, dlatego raporty są **częściowe** i nie wolno uznać pełnej regresji za zaliczoną.

Szczegółowe wyniki: `full_regression_shard_1_of_4.json` do `full_regression_shard_4_of_4.json`. Można kontynuować je poleceniem:

```
python scripts/run_full_regression.py --shard 1/4 --resume --report full_regression_shard_1_of_4.json
```

Analogicznie dla grup 2/4, 3/4 i 4/4. Po zakończeniu wszystkich grup:

```
python scripts/aggregate_full_regression.py full_regression_shard_1_of_4.json full_regression_shard_2_of_4.json full_regression_shard_3_of_4.json full_regression_shard_4_of_4.json
```

Nie uruchamiano PostgreSQL/Neon, produkcyjnych płatności ani testów przeglądarkowych.
