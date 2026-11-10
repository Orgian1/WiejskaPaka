# WiejskaPaka B/5881–B/5940 — kontrola granic uprawnień HTTP

Data: 2026-10-15. Testy na rzeczywistym lokalnym Uvicorn/HTTP, z jednorazową bazą SQLite. Nie używano Neon, zewnętrznych usług ani płatności produkcyjnych.

- Nowy `scripts/check_http_role_boundaries.py`: 35 pomyślnych kontroli HTTP (brak dostępu anonimowego do danych prywatnych, brak dostępu klienta/rolnika/dostawcy do panelu admina, dostęp do adresów wyłącznie dla dostawcy, blokada tworzenia produktów przez inne role, publiczny katalog z kwotami w groszach, wylogowanie i unieważnienie sesji).
- Endpoint testowych wypłat zwraca 404 w tej konfiguracji, ponieważ symulacja jest wyłączona; **nie** jest to dowód autoryzacji tego endpointu w trybie włączonej symulacji.
- Ponowiony `check_real_http_loopback.py`: 16/16 kontroli HTTP.
- `pytest` dwóch modułów bezpieczeństwa: 9/9 zaliczonych.
- `python -m compileall -q backend scripts` i `node --check web/app.js`: zaliczone.
- `check_chromium_real_http.py`: BLOCKED — Chromium nie może otworzyć lokalnego HTTP z powodu polityki środowiska. Nie zaliczono tego testu.
- Rzeczywista integracja PostgreSQL i testy na fizycznych telefonach nadal niezweryfikowane.

Raport JSON nowego testu: `RAPORT_B_5881_5940_HTTP_ROLE.json`.
