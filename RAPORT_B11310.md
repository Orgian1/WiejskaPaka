# WiejskaPaka B/11310 — bezpieczny plan sekwencyjny PostgreSQL

## Zmiana
- Dodano `database/test_schema_sequential.py`: generator **niewykonujący SQL** planu kolejnych 23 migracji dla nowej, pustej, jednorazowej bazy testowej.
- Weryfikuje oryginalne pliki i sumy SHA-256, kolejność, obecność tabel startowych, wybrane niebezpieczne polecenia i granice transakcji.
- Nie deklaruje fałszywej atomowości wszystkich plików. Każdy skrypt może zatwierdzać własną transakcję.
- Przy błędzie plan nakazuje przerwać, usunąć jednorazową bazę testową i rozpocząć od nowa; nie wznawiać od środka.

## Testy
`python -m pytest -q tests/test_b1129*.py tests/test_b1130*.py tests/test_b11310*.py`: **169 passed**.

## Ograniczenia
Plan nie został uruchomiony na prawdziwym PostgreSQL. To wciąż statyczna kontrola, a nie pełny parser SQL ani gwarancja poprawności migracji. Przed wykonaniem operator musi sprawdzić URL i potwierdzić, że baza jest pusta i jednorazowa. Brak płatności produkcyjnych. Docelowy tani VPS dla 30 000 opłaconych zamówień miesięcznie wymaga testów obciążenia.
