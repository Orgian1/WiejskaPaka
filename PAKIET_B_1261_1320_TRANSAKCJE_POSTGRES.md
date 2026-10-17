# WiejskaPaka — B/1261–B/1320: przenośność transakcji

- Poprawiono bezwarunkowe wywołania `BEGIN IMMEDIATE` w backendzie: to instrukcja SQLite, której nie wolno wysyłać do PostgreSQL.
- Rozpoczęcie transakcji `BEGIN IMMEDIATE` wykonywane jest teraz tylko przy lokalnym SQLite. PostgreSQL korzysta z transakcji obsługiwanych przez adapter.
- Dodano test AST, który wykrywa przyszłe bezwarunkowe użycia tego polecenia.
- Uruchomiono testy jednostkowe i wybrane testy przesyłek w izolowanych procesach.
- **Nie wykonano testu na rzeczywistym PostgreSQL**; zgodność pozostaje do weryfikacji integracyjnej.
- Nie zmieniano Neon, płatności produkcyjnych ani domeny.
