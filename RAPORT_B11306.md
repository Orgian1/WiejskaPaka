# WiejskaPaka B/11306 — offline brama migracji PostgreSQL

- Dodano `database/verify_test_migrations.py`, uruchamiany: `python -m database.verify_test_migrations`.
- Narzędzie porównuje komplet 23 zadeklarowanych plików SQL z plikami w katalogu, liczy SHA-256 i sprawdza statycznie pokrycie tabel wymaganych przy starcie.
- Niezadeklarowane pliki SQL, brakujące skrypty lub brakujące tabele skutkują kodem błędu.
- Narzędzie **nie wykonuje SQL i nie łączy się z PostgreSQL**.
- Dodano 4 testy jednostkowe.
- Regresja: **172 passed, 0 failed** (`python -m pytest -q tests/test_b1129*.py tests/test_b1130*.py tests/test_b11289_test_server_preflight.py`).
- Nadal wymagane rzeczywiste testy migracji na osobnej, pustej bazie PostgreSQL oraz przegląd zależności i kolejności skryptów. Nie jest to potwierdzenie gotowości produkcyjnej.
