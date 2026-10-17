# WiejskaPaka B/81–B/85 — kontrola sesji

- B/81: wylogowanie wszystkich sesji unieważnia oba aktywne tokeny.
- B/82: wylogowanie jednej sesji pozostawia drugą aktywną.
- B/83: unieważniony token nie może wylogować innych sesji.
- B/84: anonimowe operacje wylogowania i odczytu zamówień są odrzucane.
- B/85: kurier nie może korzystać z endpointu historii zamówień klienta.

Testy używają FastAPI TestClient i izolowanej bazy SQLite. Nie sprawdzają RLS ani realnego PostgreSQL. Żadnych zmian w Neon, domenie ani płatnościach.

Uruchomienie: `python scripts/run_tests_isolated.py -q tests/test_session_guards_b81_b85.py`.
