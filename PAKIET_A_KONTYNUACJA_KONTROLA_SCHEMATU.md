# WiejskaPaka — pakiet A, kontynuacja: kontrola schematu PostgreSQL

## Zmiany
- `backend/postgres_schema_preflight.py`: bezpieczny odczyt katalogu `information_schema` dla 11 tabel niezbędnych do podstawowych przepływów API. Wskazuje brakujące tabele, nie modyfikuje bazy i nigdy samodzielnie nie ogłasza gotowości produkcyjnej.
- `tests/test_postgres_schema_preflight.py`: trzy testy scenariuszy kompletnego, częściowego i pustego schematu.

## Testy
- Pełny zestaw na **nowej** bazie SQLite: **2402 zaliczone, 6 pominiętych, 16 podtestów zaliczonych**.
- Pierwsze uruchomienie na wcześniej użytej bazie testowej miało 19 błędów konfliktu rejestracji; ponowne uruchomienie z osobną, świeżą bazą zakończyło się sukcesem. To wskazuje na konieczność izolacji danych testowych.
- Nie uruchomiono testów na rzeczywistym PostgreSQL/Neon; brak lokalnego serwera PostgreSQL w tym środowisku.

## Blokery przed produkcją
1. Odizolowany PostgreSQL i rzeczywiste testy migracji, transakcji, blokad oraz uprawnień.
2. Weryfikacja pełnego schematu (11 tabel to tylko rdzeń; projekt ma więcej modułów).
3. Audyt RLS i egzekwowania uprawnień; RLS pozostaje wyłączony.
4. Audyt wszystkich endpointów, UI i pełnych scenariuszy.
5. Podłączenie operatora płatności dopiero po ukończeniu i testach aplikacji.

Nie zmieniono Neon, domeny ani płatności produkcyjnych.
