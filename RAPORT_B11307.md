# WiejskaPaka B/11307 — blokada sum kontrolnych SQL

- Dodano `database/test_schema_checksums.json` z SHA-256 i rozmiarami 23 plików SQL w zatwierdzonej kolejności.
- `database/schema_lock.py` weryfikuje pliki bez otwierania połączenia z bazą i bez wykonywania SQL.
- `database/verify_test_migrations.py` odmawia pozytywnego wyniku, gdy zmieni się zawartość lub kolejność plików względem manifestu.
- Testy: `python -m pytest -q tests/test_b1129*.py tests/test_b1130*.py tests/test_b11289_test_server_preflight.py` → 176 passed.
- Testy wykonano lokalnie; **nie** przeprowadzono migracji na rzeczywistym PostgreSQL. Aktualizacja locka wymaga świadomego przeglądu zmian w SQL.
