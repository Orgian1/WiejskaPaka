# Weryfikacja 08 — porównanie schematów z żywym PostgreSQL

Dodano `database/postgres_preflight.py`. Narzędzie w trybie tylko do odczytu porównuje nazwy tabel i kolumn istniejącej bazy SQLite z rzeczywistym katalogiem podłączonego PostgreSQL. Nie ujawnia DSN ani danych osobowych w raporcie. Brak niepustych tabel lub kolumn w PostgreSQL kończy kontrolę kodem 2. Tabele puste także pojawiają się w raporcie.

Przykład po przygotowaniu **oddzielnej testowej** bazy PostgreSQL i wykonaniu odpowiednich migracji SQL:

```bash
export WP_POSTGRES_DSN='postgresql://...'
python -m database.postgres_preflight --sqlite /sciezka/do/kopii/testowej.sqlite
```

To nie jest migrator i nie potwierdza zgodności typów, constraints, sekwencji, indeksów ani działania aplikacji na PostgreSQL. Migrator v1 nadal blokuje dodatkowe niepuste tabele; nie wolno go używać do pełnej migracji danych bez rozbudowy. Płatności produkcyjne wyłączone. Strona publiczna bez zmian.
