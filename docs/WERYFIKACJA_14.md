# Weryfikacja 14 — PostgreSQL: rozróżnienie tabel i widoków

Poprzednie zapytania do `information_schema.columns` uwzględniały również widoki. Migrator próbowałby zablokować widok instrukcją `LOCK TABLE`, co może zakończyć migrację błędem. Obecnie narzędzie weryfikacji oraz migrator filtrują `information_schema.tables` po `table_type = BASE TABLE`.

**Ograniczenia:** nie wykonano testów na żywym PostgreSQL. Nie jest to potwierdzenie poprawności pełnej migracji.
