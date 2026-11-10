# Pakiet 4/5 — audyt schematu i testy integracyjne

Dodano `backend/schema_audit.py`: porównanie tabel tworzonych przez kod lokalny SQLite z tabelami deklarowanymi w głównym schemacie PostgreSQL i wszystkich skryptach `upgrade_*.sql`. Skrypt domyślnie **nie łączy się z bazą**. Zwraca kod wyjścia 1, gdy w skryptach PostgreSQL brakuje tabel.

```bash
python -m backend.schema_audit
python -m pytest -q tests
```

Aby sprawdzić obecność tabel na **własnej, wcześniej przygotowanej testowej instancji PostgreSQL**, podaj `WP_AUDIT_POSTGRES_DSN` i uruchom ten sam skrypt. Połączenie jest wyłącznie do odczytu metadanych `information_schema`; skrypt niczego nie migruje. Nie przekazuj hasła w publicznych logach. Nie używaj produkcyjnej bazy do eksperymentów.

**Wynik lokalny:** 124 testy; wszystkie tabele zadeklarowane w kodzie SQLite występują w plikach schematu/migracji PostgreSQL. To **nie dowodzi** poprawności typów, indeksów, kolejności migracji ani działania zapytań na PostgreSQL.

**Ograniczenia:** środowisko testowe nie ma uruchomionej instancji PostgreSQL; nie wykonano realnych testów integracyjnych z PostgreSQL. Przed wdrożeniem należy uruchomić bazę testową, wykonać migracje w kolejności, przeprowadzić scenariusze API end-to-end (rejestracja → zakup → PIN → płatność testowa → rozliczenie) oraz testy współbieżności, odtwarzania kopii i uprawnień. Nie ma jeszcze integracji z operatorem płatności. Publiczna strona pozostaje bez zmian.
