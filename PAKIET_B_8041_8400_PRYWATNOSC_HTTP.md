# WiejskaPaka — pakiet B/8041–B/8400: prywatność API przez HTTP

Rozszerzono skrypt `scripts/audit_cross_account_http.py` o rekurencyjną kontrolę pól telefonicznych w odpowiedziach JSON publicznego katalogu, list zamówień klientów i rolnika oraz historii zdarzeń zamówienia. Kontrola uruchamia rzeczywisty lokalny HTTP FastAPI na jednorazowej bazie SQLite i sześciu kontach testowych.

## Wyniki uruchomienia
- Rozszerzony audyt HTTP: **52/52 kontroli**, status PASS (w tym 6 nowych żądań prywatności i 6 kontroli struktury pól).
- Regresja dostaw i PIN: **5 testów zaliczonych**.
- Nowy test kontraktu audytu: **1 test zaliczony**.
- `node --check web/app.js` i `python -m compileall -q backend scripts`: PASS.

## Ograniczenia
Kontrola wykrywa wymienione klucze telefoniczne w JSON; nie wykrywa numerów ukrytych w dowolnym polu tekstowym. Nie jest to pełny audyt prywatności ani gwarancja bezpieczeństwa. Nie wykonywano testów PostgreSQL ani fizycznych telefonów. Nie podłączano Neon, płatności produkcyjnych, hostingu ani domeny.
