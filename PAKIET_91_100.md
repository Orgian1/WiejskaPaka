# Pakiet 91–100: poprawka zgodności blokady logowania z PostgreSQL

- `backend/time_safety.py`: bezpieczna normalizacja znaczników czasu ze SQLite (tekst) i psycopg (datetime).
- `backend/app.py`: blokada po nieudanych logowaniach obsługuje oba typy danych. Poprzedni `datetime.fromisoformat(...)` zgłaszał TypeError dla natywnego `datetime` z PostgreSQL.
- Testy graniczne obejmują różne strefy czasowe, równość terminu, format `Z` i odrzucanie dat bez strefy.

## Ograniczenia

Numeracja pakietu jest organizacyjna, nie oznacza wykonania dziesięciu oddzielnych funkcji. Testy lokalne nie dowodzą zgodności ze schematem Neon. RLS nadal wyłączony, brak płatności produkcyjnych. Nie wykonywano migracji ani zmian publicznej strony.
