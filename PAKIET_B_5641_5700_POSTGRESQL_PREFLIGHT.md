# WiejskaPaka — B/5641–B/5700 — PostgreSQL: weryfikacja bezpieczna offline

Data: 2026-10-15.

## Faktycznie wykonane

- `python -m pytest -q tests/test_postgres* tests/test_b1261_postgres_transaction_portability.py tests/test_b461_checkout_postgres_locking.py`
- Wynik: **53 passed, 6 skipped**, kod wyjścia 0.
- `node --check web/app.js` — sukces.
- `python -m compileall -q backend scripts` — sukces.
- Brak lokalnego serwera `postgres` i `pg_ctl`; `WP_TEST_DATABASE_URL` nie jest ustawione.
- Brak uruchomionych testów wymagających rzeczywistej bazy PostgreSQL. Sześć testów pominięto; nie wolno przedstawiać ich jako zaliczonych.
- Nie modyfikowano konfiguracji Neon, nie podłączano zewnętrznej bazy, płatności ani hostingu.

## Wnioski

Testy jednostkowe i testy zabezpieczeń/adaptera PostgreSQL zaliczono w środowisku offline. **Integracja z rzeczywistą bazą PostgreSQL nie jest zweryfikowana.** Kolejny etap wymaga lokalnego, jednorazowego PostgreSQL z bazą nazwaną `*_test` lub `wp_test_*`, ewentualnie jawnie zatwierdzonej bazy staging. Nie używać produkcyjnego Neon.

## Następne kontrole

1. Zainstalować PostgreSQL i sterownik `psycopg` w izolowanym środowisku.
2. Uruchomić bazę testową, ustawić wyłącznie `WP_TEST_DATABASE_URL` dla jednorazowej bazy.
3. Wykonać opcjonalne testy transakcji, blokad i rollbacku; odnotować wyniki i pominięcia.
4. Oddzielnie sprawdzić rzeczywisty serwer HTTP oraz testy fizycznych telefonów.

**Bramka produkcyjna pozostaje zamknięta.**
