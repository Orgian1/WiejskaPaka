# Weryfikacja 05 — współbieżność i test PostgreSQL (opt-in)

- Test współbieżności sprawdza, czy dwie jednoczesne próby zakupu jednej dostępnej sztuki skutkują dokładnie jednym zamówieniem (HTTP 201) i jedną odmową (HTTP 409).
- Test opt-in weryfikuje połączenie z prawdziwym PostgreSQL, podstawowe zapytania, parametry i rollback. Bez `WP_TEST_POSTGRES_DSN` jest **pomijany**, a nie uznawany za pomyślny test integracyjny.
- Aby uruchomić test PostgreSQL: ustaw `WP_TEST_POSTGRES_DSN` na adres **izolowanej bazy testowej** i uruchom `python -m pytest -q tests/test_postgres_live_optin.py`.
- Test połączenia **nie** dowodzi, że wszystkie migracje i operacje aplikacji są kompatybilne z PostgreSQL. Pełne testy migracji i API na PostgreSQL pozostają zadaniem otwartym.
- Nie podłączono płatności produkcyjnych, hostingu ani domeny.
