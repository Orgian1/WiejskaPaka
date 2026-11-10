# Weryfikacja 09 — manifest danych przed migracją

Nowe narzędzie `database/migration_snapshot.py` tworzy **manifest wszystkich tabel SQLite**, liczby rekordów, listy kolumn i skróty SHA-256 zawartości, bez eksportowania surowych danych osobowych.

Przy wstrzymanych zapisach do bazy:

```bash
python -m database.migration_snapshot --sqlite sciezka/do/bazy.sqlite --save manifest.json
python -m database.migration_snapshot --sqlite sciezka/do/bazy.sqlite --verify manifest.json
```

Druga komenda kończy się kodem 2, jeśli zawartość lub struktura dowolnej tabeli uległa zmianie. Manifest służy do wykrywania zmian źródła **przed migracją**, a nie do potwierdzania poprawności przeniesienia danych do PostgreSQL. Hash nie jest szyfrowaniem; manifest również należy chronić. Baza SQLite jest otwierana tylko do odczytu, z jedną transakcją odczytu.

**Nadal brakuje:** pełnego migratora wszystkich tabel, uruchomionej testowej instancji PostgreSQL, testów end-to-end w PostgreSQL, audytu bezpieczeństwa i integracji operatora płatności. Nie uruchamiać produkcyjnie.
