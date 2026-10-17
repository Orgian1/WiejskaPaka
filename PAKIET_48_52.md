# WiejskaPaka — pakiet zbiorczy 48–52

## Zmiana rzeczywista
- `POST /test/payments/{order_id}/events` korzysta z `order_write_db` i otrzymuje nagłówek `Authorization`.
- W trybie PostgreSQL sesja i rola (`klient` albo `rolnik`) są ponownie weryfikowane wewnątrz transakcji zapisu, przed odczytem zamówienia z `FOR UPDATE` i przed zmianą symulowanej płatności.
- Zachowano weryfikację właściciela zamówienia, statusów oraz flagę `WP_ENABLE_TEST_PAYMENTS`.
- Dodano trzy testy regresyjne: przekazanie tokenu do mechanizmu autoryzacji, odrzucenie nieważnej sesji i domyślne wyłączenie symulacji.

## Weryfikacja
`WIEJSKAPAKA_DB=<nowa pusta ścieżka sqlite> python -m pytest -q`: **1322 passed, 3 skipped, 16 subtests passed**.
Uwaga: uruchomienie na dołączonej przykładowej bazie SQLite może powodować konflikty danych testowych; testy uruchomiono z nową, izolowaną bazą.

## Pozostałe ryzyka
- Nie wykonano testów integracyjnych na rzeczywistym PostgreSQL/Neon.
- RLS jest wyłączony, a polityki nie są wdrożone.
- Nadal trzeba przejrzeć pozostałe endpointy zapisu i zgodność transakcji.
- Płatności i wypłaty są wyłącznie symulacjami; nie podłączono operatora płatności ani KSeF.
- Nie dokonano zmian w bazie Neon ani w publicznej witrynie.
