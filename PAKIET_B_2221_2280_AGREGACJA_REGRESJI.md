# WiejskaPaka — B/2221–B/2280: weryfikacja kompletności regresji

## Dodano
- `scripts/aggregate_full_regression.py`: łączy raporty części regresji w jedno podsumowanie.
- Odrzuca niekompletne raporty, nieznane nazwy testów i powtórzenia modułów.
- Zgłasza brakujące moduły oraz moduły, które nie przeszły testów.
- Zapisuje wynik atomowo do JSON i zwraca niezerowy kod wyjścia, jeśli regresja nie jest kompletna i poprawna.
- `tests/test_b2221_regression_aggregation.py`: cztery testy nowego mechanizmu.

## Uruchomienie po wykonaniu wszystkich czterech fragmentów
```
python scripts/run_full_regression.py --shard 1/4
python scripts/run_full_regression.py --shard 2/4
python scripts/run_full_regression.py --shard 3/4
python scripts/run_full_regression.py --shard 4/4
python scripts/aggregate_full_regression.py full_regression_shard_1_of_4.json full_regression_shard_2_of_4.json full_regression_shard_3_of_4.json full_regression_shard_4_of_4.json
```

## Weryfikacja
- Nowe testy: 4/4 PASS.
- Próbka izolowanych modułów: 3/3 PASS.
- Kompilacja backend i scripts: PASS.
- Pełna regresja wszystkich modułów: NIE URUCHOMIONA.
- Testy PostgreSQL i przeglądarkowe: NIE URUCHOMIONE.

Bez zmian w konfiguracji Neon, hostingu, domenie i płatnościach produkcyjnych.
