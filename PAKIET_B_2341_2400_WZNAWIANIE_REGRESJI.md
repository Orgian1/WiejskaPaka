# WiejskaPaka B/2341–B/2400 — wznawianie pełnej regresji

## Zmiany
- `scripts/run_tests_per_file.py`: opcja `--resume` wznawia przerwany raport, ponownie uruchamia tylko testy niezaliczone i jeszcze niewykonane.
- `scripts/run_full_regression.py`: przekazanie `--resume` do wykonawcy shardów.
- Przed wznowieniem: walidacja pełnej listy modułów, kolejności i sum SHA-256; zmieniony plan lub test powoduje odmowę wznowienia.
- Zaliczone moduły zachowują wyniki; niezakończone są ponawiane. Raport pozostaje zapisywany atomowo.
- Dodano cztery testy regresyjne funkcji wznowienia.

## Uruchomienie
`python scripts/run_full_regression.py --shard 1/4 --timeout 90`

Po przerwaniu:
`python scripts/run_full_regression.py --shard 1/4 --timeout 90 --resume`

Po zmianie kodu testów należy uruchomić shard od nowa (bez `--resume`).

## Zakres potwierdzony
Testy mechanizmu wznowienia oraz istniejące testy shardowania. Pełna regresja, PostgreSQL i testy w przeglądarce nadal nie są zakończone. Nie zmieniono produkcyjnych integracji.
