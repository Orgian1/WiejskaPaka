# Pakiet A — poprawka odczytu wyników PostgreSQL RETURNING

## Naprawiony błąd
Adapter PostgreSQL pobierał i usuwał pierwszy wiersz wyniku dla każdego
zapytania kończącego się `RETURNING id`, także gdy programista jawnie
umieścił tę klauzulę w zapytaniu. W takim przypadku wywołanie `fetchone()`
przez kod aplikacji zwracało `None` zamiast identyfikatora.

Po zmianie adapter konsumuje wynik **tylko** wtedy, gdy sam dopisał
`RETURNING id` w celu emulacji SQLite `lastrowid`. Jawne `RETURNING`
pozostaje dostępne dla wywołującego. Dodano cztery testy regresyjne.

## Testy
`python scripts/run_tests_isolated.py -q`

Wynik: **2413 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych**.
Pominięte testy wymagają odrębnego serwera PostgreSQL. Wynik lokalny
nie potwierdza zgodności z produkcyjną bazą Neon.

## Niezmienione elementy
Nie wykonywano migracji na Neon, nie włączano RLS, nie zmieniano
wiejskapaka.pl ani nie uruchamiano płatności rzeczywistych.
