# WiejskaPaka — pakiet B/2161–B/2220

## Dodano
- `scripts/run_full_regression.py`: deterministyczny podział wszystkich modułów `tests/test_*.py` na fragmenty (`--shard 1/4` itd.).
- Każdy moduł wykonywany osobno w odizolowanym procesie i na osobnej bazie SQLite dzięki istniejącemu `run_tests_per_file.py`.
- Walidacja błędnych numerów fragmentów, pustej listy testów i timeoutu; raport JSON dla każdego fragmentu.
- `tests/test_b2161_full_regression_runner.py`: kontrola pełnego i bezpowtórzeniowego pokrycia listy testów przez fragmenty oraz błędnych argumentów.

## Uruchamianie
```
python scripts/run_full_regression.py --shard 1/4
python scripts/run_full_regression.py --shard 2/4
python scripts/run_full_regression.py --shard 3/4
python scripts/run_full_regression.py --shard 4/4
```
Aby uruchomić wszystko w jednym procesie nadrzędnym: `python scripts/run_full_regression.py` (może potrwać wiele minut).

## Weryfikacja tego pakietu
- Nowe testy: 3 passed.
- Próba regresji wybranych czterech modułów: 4/4 PASS; zapis `regression_b2161_smoke.json`.
- `python -m compileall -q backend scripts`: PASS.

## Ograniczenia
Nie uruchomiono jeszcze pełnej regresji wszystkich modułów. Nie testowano rzeczywistej przeglądarki ani PostgreSQL. Brak zmian w Neon, domenie, hostingu i płatnościach produkcyjnych.
