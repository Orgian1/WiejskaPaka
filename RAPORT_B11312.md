# WiejskaPaka B/11312 — weryfikacja schematu po migracjach

Dodano odczytową kontrolę faktycznej bazy PostgreSQL po wykonaniu wszystkich 23 plików migracyjnych. Kontrola potwierdza nazwę bazy testowej, brak uprzywilejowanej roli, obecność 14 tabel potrzebnych do uruchomienia API i kolumn odczytywanych przez lifespan. Procedura migracji wywołuje ją na końcu; błędy blokują dalszy etap i nie ujawniają danych połączenia.

Testy: `python -m pytest -q tests/test_b1129*.py tests/test_b1130*.py tests/test_b1131*.py` — 183 zaliczone, 0 błędów.

Ograniczenia: nie uruchomiono rzeczywistego PostgreSQL, nie wykonano migracji ani testów obciążeniowych. Kontrola nie potwierdza pełnej zgodności typów, indeksów, RLS i wszystkich endpointów. Kolejny etap wymaga lokalnej/tymczasowej instancji PostgreSQL, niekoniecznie płatnego VPS. Produkcyjne płatności pozostają wyłączone.
