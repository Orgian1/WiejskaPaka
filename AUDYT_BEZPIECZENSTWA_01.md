# Audyt bezpieczeństwa — pakiet 01

## Zmiany w kodzie
- `GET /orders/{order_id}/location` korzysta z `order_write_db` w PostgreSQL, czyli ponownie weryfikuje token i rolę w tej samej transakcji, w której pobierany jest adres.
- `POST /auth/logout-all` ponownie weryfikuje sesję przed usunięciem wszystkich sesji konta.
- SQLite zachowuje dotychczasowy lokalny przepływ.
- Dodano 4 testy regresyjne obu operacji, w tym odrzucanie nieważnego tokenu.

## Weryfikacja
`WIEJSKAPAKA_DB=/tmp/wp_release_fresh_20261014.sqlite3 python -m pytest -q`

Wynik: 1354 passed, 4 skipped, 16 subtests passed.

## Pozostałe blokery produkcyjne
- Brak rzeczywistego testu integracyjnego z Neon/PostgreSQL.
- RLS pozostaje wyłączony; sam kontekst transakcji nie stanowi izolacji bazy.
- Należy skontrolować pozostałe endpointy pod kątem dostępu do danych i współbieżności.
- Brak produkcyjnego operatora płatności i wypłat.
- Nie wdrażano ani nie modyfikowano publicznej strony.
