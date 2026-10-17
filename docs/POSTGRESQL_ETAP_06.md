# Etap backend 06 — przygotowanie migracji PostgreSQL

Wykonano: schemat PostgreSQL z kluczami obcymi, indeksami, ograniczeniami kwot w groszach, migrator danych z lokalnej SQLite i testy walidacji źródła.

## Przebieg bezpiecznej migracji
1. Zatrzymaj aplikację i wykonaj kopię SQLite (oraz kopię PostgreSQL, jeśli dotyczy).
2. Utwórz PUSTĄ bazę PostgreSQL w środowisku testowym i uruchom `psql -v ON_ERROR_STOP=1 -f database/postgres_schema.sql`.
3. Zainstaluj `psycopg[binary]` w środowisku migracji.
4. Uruchom `python -m database.migrate_sqlite_to_postgres --sqlite /ścieżka/do/wiejskapaka.sqlite3` (dry run).
5. Ustaw `WP_POSTGRES_DSN` bez ujawniania hasła w terminalowej historii.
6. Uruchom migrator ponownie z `--execute`.
7. Zweryfikuj dane, powiązania, uprawnienia i testy API **z nowym adapterem PostgreSQL** przed przełączeniem ruchu.

## Istotne ograniczenia
- **Bieżący backend nadal korzysta z SQLite**. Migrator przenosi dane, ale sam nie przełącza FastAPI na PostgreSQL.
- Schemat przechowuje dotychczasowe daty jako TEXT dla zgodności migracji; przed produkcją należy przejść na TIMESTAMPTZ i przetestować konwersję.
- Import wymaga pustych tabel; nie wykonuj go na produkcyjnej bazie z danymi.
- Nie uruchomiono testu na prawdziwym serwerze PostgreSQL (brak serwera w środowisku).
- Migracja nie zapewnia jeszcze pełnego audytu finansowego, dostawców, fakturowania ani produkcyjnych płatności.
