# B/3961–B/4020 — diagnostyka pełnej regresji

- Potwierdzono, że uruchamianie wszystkich testów w jednej bazie SQLite daje sztuczny konflikt: `test_b1141_isolation_probe_a.py` i `test_b1141_isolation_probe_b.py` oba tworzą tabelę `marker`.
- Dodano ostrzeżenie do `scripts/run_tests_isolated.py`: izoluje on bazę na poziomie procesu, a nie każdego modułu. Pełną regresję należy wykonywać przez `scripts/run_full_regression.py`.
- Uruchomiono jeden z ośmiu shardów regresji, z izolacją bazy dla każdego modułu. Częściowy raport: `regression_1of8.json`. Raport NIE jest dowodem zaliczenia całej regresji.
- Nie dotykano Neon, płatności rzeczywistych ani hostingu.
