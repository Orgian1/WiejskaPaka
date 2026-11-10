# PostgreSQL — pakiet 04: testy transakcyjne (opt-in)

Dodano dwa opcjonalne testy integracyjne `tests/test_postgres_transaction_integration_optional.py`:
- wykonanie parametryzowanego INSERT/SELECT na tabeli tymczasowej i sprawdzenie zakończenia transakcji;
- wymuszony wyjątek i kontrola, czy po wycofaniu transakcji można wykonać nowe zapytanie.

Testy wymagają `WP_TEST_DATABASE_URL` wskazującego **wydzieloną bazę testową** i przejścia `require_disposable_postgres`. Nie należy podawać produkcyjnego adresu Neon. Bez adresu testy są pomijane, co NIE oznacza pomyślnej integracji z PostgreSQL.

Testy nie modyfikują trwałych tabel. Używają `CREATE TEMP TABLE`, a testy pozostałych modułów nadal działają lokalnie na SQLite. Nie włączono RLS, nie podłączono płatności ani nie wdrożono aplikacji.

Następne wymagane kroki: uruchomienie testów na izolowanym PostgreSQL, testy wielosesyjne zamówień i uprawnień, weryfikacja polityk RLS na oddzielnym koncie oraz pełny audyt wdrożeniowy.
