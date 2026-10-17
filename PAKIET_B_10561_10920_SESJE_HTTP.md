# WiejskaPaka B/10561–B/10920 — audyt sesji przez rzeczywisty HTTP

## Wykonane zmiany
- Dodano `scripts/audit_session_revocation_http.py`: niezależny audyt rzeczywistego HTTP na lokalnym serwerze Uvicorn i jednorazowej bazie SQLite.
- Dodano `tests/test_b10561_session_revocation_http.py`: automatyczny test regresyjny.
- Zweryfikowano trzy jednoczesne sesje klienta i trzy rolnika, unikalność tokenów, błędne nagłówki, wylogowanie pojedynczej sesji, wylogowanie wszystkich sesji, brak wpływu wylogowania klienta na sesje rolnika, ponowne logowanie.
- Zapisano pełne wyniki 41 kontroli oraz raport akceptacyjny HTTP.

## Wyniki
- Audyt sesji: **41/41 PASS**.
- Nowy test pytest: **1/1 PASS**.
- Akceptacja HTTP: **4/4 zestawy PASS**.
- `node --check web/app.js`: PASS.
- `python -m compileall -q backend scripts`: PASS.

## Granice audytu
Testy dotyczą wyłącznie lokalnego HTTP i izolowanej SQLite. Nie przeprowadzono rzeczywistej integracji PostgreSQL, testów na fizycznym telefonie ani pełnego audytu produkcyjnego. Żadne rzeczywiste płatności ani usługi Neon nie były używane.
