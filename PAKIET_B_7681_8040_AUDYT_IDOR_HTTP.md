# WiejskaPaka — pakiet B/7681–B/8040

## Wykonane
- Dodano `scripts/audit_cross_account_http.py`: prawdziwy lokalny HTTP z FastAPI i jednorazową SQLite.
- Utworzono sześć odrębnych kont: dwóch klientów, dwóch rolników, dwóch kurierów.
- Przetestowano odmowy dostępu do cudzych zdarzeń zamówienia, adresu, potwierdzenia, rozliczeń i wysyłki.
- Sprawdzono dostęp właścicieli do historii i podglądu rozliczenia, izolację list zamówień oraz pojedynczą opłatę za dostawę (2×349+501=1199 groszy).
- Dodano test regresyjny `tests/test_b7681_cross_account_http.py`.

## Wyniki
- Scenariusz HTTP: **40/40 kontroli zaliczonych**. Raport: `RAPORT_B_7681_8040_IDOR_HTTP.json`.
- Testy pytest (nowy scenariusz + wcześniejsza izolacja kont): **6/6 zaliczonych**.
- `node --check web/app.js`: OK; `python -m compileall -q backend scripts`: OK.

## Granice
Testy obejmują wybrane krytyczne trasy i scenariusze. Nie stanowią kompletnego audytu IDOR wszystkich metod API. Nie uruchamiano PostgreSQL, Neon, rzeczywistych płatności, hostingu ani domeny. Pozostają testy fizycznych urządzeń, Chromium przez rzeczywisty HTTP, PostgreSQL i przegląd prawny.
