# WiejskaPaka B/11295 — brama schematu PostgreSQL

- Prywatny launcher weryfikuje rzeczywistą nazwę bazy, a następnie obecność wszystkich tabel krytycznych dla API.
- Zapytanie do `information_schema.tables` jest parametryzowane i tylko do odczytu.
- Brak dowolnej wymaganej tabeli blokuje uruchomienie HTTP.
- Błędna nazwa bazy jest wykrywana przed sprawdzaniem schematu.
- Po błędzie zamykane jest połączenie z bazą.
- 82 testy PASS w 7 modułach B/11289–B/11295.
- Nie wykonywano testu na żywym PostgreSQL. Nie uruchamiano płatności produkcyjnych.
