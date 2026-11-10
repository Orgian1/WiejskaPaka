# WiejskaPaka — B/3001–B/3060: kompletna regresja lokalna

- Naprawiono możliwość wznawiania raportów z modułami testowymi zmienionymi po wcześniejszym przebiegu: opcja `--refresh-stale` uruchamia ponownie wyłącznie zmienione testy, a wyniki pozostałych zaliczonych i niezmienionych testów wykorzystuje ponownie.
- Domyślne zachowanie `--resume` nadal odrzuca raport z nieaktualną sumą kontrolną.
- Dodano test nowego trybu w `tests/test_b2341_resume_regression.py`.
- Uruchomiono cztery grupy regresji z `--resume --refresh-stale`, a następnie agregator zweryfikował zgodność sum SHA-256 oraz kompletność planu.
- Wynik: 200/200 modułów zaliczonych, 0 niepowodzeń, 0 brakujących. **Uwaga:** część modułów została zaliczona w poprzednich przebiegach i użyta ponownie po weryfikacji sum kontrolnych, nie wykonano wszystkich 200 od zera w tej sesji.
- `python -m pytest -q tests/test_b2341_resume_regression.py`: 5 passed.
- `python -m compileall -q backend scripts`: OK.
- Raport: `full_regression_summary_3001.json`.
- Nadal brak rzeczywistych testów przeglądarkowych i PostgreSQL. Płatności pozostają testowe. Konfiguracji Neon nie zmieniano.

Ponowne uruchomienie:
`python scripts/run_full_regression.py --shard 1/4 --resume --refresh-stale`
Analogicznie dla 2/4, 3/4 i 4/4.
Agregacja z katalogu projektu:
`python -m scripts.aggregate_full_regression full_regression_shard_{1,2,3,4}_of_4.json --output full_regression_summary_3001.json`
