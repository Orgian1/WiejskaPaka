# Weryfikacja 07 — inwentaryzacja przed migracją

Dodano narzędzie `database/migration_inventory.py` uruchamiane w trybie tylko do odczytu:

`python -m database.migration_inventory --sqlite /sciezka/do/bazy.db`

Raport JSON podaje liczbę rekordów w każdej tabeli SQLite, kontrolę integralności,
błędy kluczy obcych oraz informację, czy istnieje deklaracja tabeli w plikach SQL PostgreSQL.
Narzędzie kończy się kodem 2, gdy wykryje uszkodzenie bazy, błędne klucze obce lub
niepustą tabelę bez deklaracji PostgreSQL.

**Istotne ograniczenia:** obecność `CREATE TABLE` nie dowodzi zgodności kolumn,
indeksów, typów danych, kolejności migracji ani zachowania wszystkich rekordów.
Narzędzie nie kopiuje danych i nie oznacza pełnej migracji jako bezpiecznej.
Migrator v1 pozostaje ograniczony do ośmiu tabel. Produkcyjna migracja jest zablokowana
organizacyjnie do czasu pełnego mapowania schematów i testów na PostgreSQL.
