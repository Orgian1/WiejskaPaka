# WiejskaPaka — B/51–B/55: bezpieczeństwo nieudanej dostawy (testowo)

Zmiana dotyczy **wyłącznie symulacji** płatności i dostaw. Nie wykonuje przelewów ani nie kontaktuje się z operatorem płatności.

- **B/51:** zdarzenie `delivery_failed_by_courier_test` jest odrzucane, jeśli dostawa jeszcze nie ruszyła.
- **B/52:** przy zaakceptowaniu nieudanej dostawy następuje w tej samej transakcji zapis pełnego zwrotu w groszach oraz zmiana statusu zamówienia na `nieudana_dostawa_testowo`. Odbiera to kurierowi dostęp do adresu klienta.
- **B/53:** ponowienie *identycznego* identyfikatora zdarzenia pozostaje idempotentne; nowy identyfikator dla kolejnego zwrotu jest odrzucany.
- **B/54:** klient i kurier nie mogą samodzielnie zgłosić zdarzenia finansowego nieudanej dostawy — uprawnienie ma tylko właściwy rolnik.
- **B/55:** nie można zgłosić nieudanej dostawy po zakończeniu zamówienia prawidłowym PIN-em.

Zmiany: `backend/app.py`, `scripts/check_browser_backend_bridge.py`, `tests/test_package_b51_b55.py`.

## Sprawdzenie

- `python -m pytest -q` — 2507 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych.
- `python -m scripts.check_browser_backend_bridge` — pełny dotychczasowy scenariusz Chromium + FastAPI + SQLite zaliczony (79 żądań przez most w procesie).

## Ograniczenia

Nie sprawdzono produkcyjnego PostgreSQL/Neon, polityk RLS, realnego HTTP na serwerze ani prawdziwych płatności. **Weryfikacja reguł RLS i przejść stanów w PostgreSQL jest konieczna przed wdrożeniem.** Nie zmieniono publicznej strony ani zewnętrznej bazy.
