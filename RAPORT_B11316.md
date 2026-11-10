# WiejskaPaka B/11316 — przenośny plan migracji PostgreSQL

- Poprawiono generator `database/generate_test_migration_plan.py`.
- Plan ma nagłówek `#!/bin/sh`, `set -eu`, ustawia katalog roboczy względem własnej lokalizacji.
- Przed migracjami sprawdza dostępność `python` i `psql`, blokadę SHA-256 oraz dedykowaną pustą bazę.
- Zapis planu korzysta z `O_EXCL`, nie nadpisuje istniejącego pliku nawet przy równoległym uruchomieniu generatora.
- Dodano testy struktury, składni shell i nieprawidłowego planu.
- Wynik: 190 passed (`python -m pytest -q tests/test_b1129*.py tests/test_b113*.py`).
- Nie wykonywano migracji na żywym PostgreSQL; plan jest sekwencyjny, nieatomowy. W razie błędu wymagana jest nowa pusta baza testowa.
- Serwer VPS nie jest jeszcze wymagany do pracy nad kodem, ale do testu bazy konieczna będzie działająca instancja PostgreSQL.
