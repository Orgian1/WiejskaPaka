# WiejskaPaka B/11294 — weryfikacja docelowej bazy

- Przed uruchomieniem serwera HTTP program wykonuje połączenie z PostgreSQL (limit połączenia 5 s).
- Odczytuje `SELECT current_database()` i porównuje dokładną nazwę z zatwierdzoną w preflight.
- Nie uruchamia API przy braku połączenia, błędzie zapytania lub niezgodności nazwy.
- Zamyka połączenie również w przypadku niezgodności lub błędu.
- Nie tworzy ani nie modyfikuje schematu bazy.

Testy: `python -m pytest -q tests/test_b11294_database_probe.py tests/test_b11293_database_name_guard.py tests/test_b11292_postgres_transport.py tests/test_b11291_private_port.py tests/test_b11290_private_launcher.py tests/test_b11289_test_server_preflight.py`

Wynik: **74 passed, 0 failed**.

Ograniczenia: połączenie jest mockowane; brak rzeczywistego PostgreSQL, migracji i testów integracyjnych. Nie uruchomiono płatności produkcyjnych.
