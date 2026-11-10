# WiejskaPaka B/9841–B/10200 — skoncentrowana regresja bezpieczeństwa

## Wykonano
- Dodano `scripts/run_security_focus_isolated.py` — 45 modułów pytest wybranych według obszarów auth, permission, privacy, payment, refund, postgres, delivery, shipment, security.
- Każdy moduł uruchomiony w osobnym procesie i na oddzielnej, tymczasowej bazie SQLite.
- Usuwane są zmienne środowiskowe mogące kierować do Neon/produkcyjnego PostgreSQL.
- Wyniki są zapisywane po każdym module i możliwe do wznowienia.
- **45/45 modułów zakończyło się kodem 0**, bez niezaliczonych modułów.
- `node --check web/app.js` oraz `python -m compileall -q backend scripts` zakończone poprawnie.
- Ponowiono próbę Chromium → localhost HTTP: **BLOCKED**, 0 zaliczonych kroków, polityka środowiska `ERR_BLOCKED_BY_ADMINISTRATOR`.

## Ograniczenia
- Moduł pytest z kodem 0 może zawierać pominięte testy (np. wymagające PostgreSQL). Raport zapisuje końcowy komunikat pytest dla każdego modułu; nie wolno utożsamiać 45 modułów z 45 testami ani z pełnym testem PostgreSQL.
- Nie uruchomiono serwera PostgreSQL; brak lokalnego `postgres`/`pg_ctl` i sterownika `psycopg`.
- Nie przeprowadzono testu na fizycznym telefonie ani końcowego audytu prawnego.
- Płatności produkcyjne, Neon, hosting i domena pozostają niepodłączone.

## Pliki
- `RAPORT_B_9841_10200_BEZPIECZENSTWO_IZOLACJA.json` — szczegóły każdego modułu.
- `scripts/run_security_focus_isolated.py` — powtarzalny test z checkpointem.
