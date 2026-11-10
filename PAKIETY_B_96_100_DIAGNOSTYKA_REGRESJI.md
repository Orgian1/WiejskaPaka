# Pakiety B/96–B/100 — diagnostyka pełnej regresji

Wcześniejsze pełne przebiegi pytest przekraczały limit czasu; nie uznajemy ich za zaliczone. Dodano `scripts/run_regression_chunks.py`, który dzieli testy według plików na partie, uruchamia każdą na osobnej tymczasowej bazie SQLite, ustawia limit czasu każdej partii i zapisuje JSON z kodem wyjścia oraz końcówką logu (również w razie błędu). Żadne dane dostępowe PostgreSQL nie są przekazywane do procesów testowych.

Uruchomienie: `python scripts/run_regression_chunks.py --batch-size 12 --timeout 90 --report wynik.json`.

Partie są izolowane względem siebie, więc wynik nie zastępuje pojedynczego pełnego przebiegu i może ujawnić testy zależne od współdzielonego stanu. Narzędzie nie łączy się z Neon ani nie zmienia publicznej strony.
