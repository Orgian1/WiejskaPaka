# WiejskaPaka B/2461–B/2520 — kontynuacja regresji

- Uruchomiono trzecią grupę (12 modułów) i czwartą grupę (12 modułów) na izolowanych bazach SQLite. Obie grupy zakończyły się wynikiem PASS.
- Grupa 3 została przerwana po 11 zaliczonych modułach wskutek limitu wykonania; następnie ukończono ją przez nowy mechanizm `--resume` bez powtarzania tych 11 testów.
- Rozszerzono `scripts/run_regression_chunks.py` o `--resume`, który wykorzystuje tylko zaliczone moduły z raportu, odrzuca zmieniony manifest i niezgodny zakres uruchomienia oraz ponawia testy niezaliczone.
- Dodano 3 testy nowego mechanizmu: wznowienie, odrzucenie zmienionych testów, ponowienie niezaliczonego modułu.
- Przykład: `python scripts/run_regression_chunks.py --only-batch 5 --report regression_batch5.json --resume`.
- To nie jest pełna regresja projektu; pozostałe grupy nie zostały jeszcze wykonane w tym pakiecie. Nie wykonano testów na PostgreSQL ani przeglądarkowych.
- Nie zmieniano konfiguracji Neon, domeny ani płatności produkcyjnych.
