# WiejskaPaka — B/6181–B/6240: powtarzalna akceptacja HTTP

Dodano `scripts/run_http_acceptance_suite.py`, jeden punkt uruchomienia czterech niezależnych zestawów kontroli. Raport maszynowy: `RAPORT_HTTP_AKCEPTACJA.json`.

## Wyniki 2026-10-15
- HTTP loopback z lokalnym FastAPI: 16 kontroli, zaliczone.
- Zakup, dostawa i zwrot przez HTTP: 34 kontrole, zaliczone.
- Koszyk wielu rolników, jedna dostawa na przesyłkę i odbiór w wycenie: 36 kontroli, zaliczone.
- Prywatność i dostawa: 9 testów pytest, zaliczone.
- JavaScript `node --check web/app.js`: zaliczony.
- Python `compileall backend scripts`: zaliczony.

## Granice dowodu
Testy wykorzystują jednorazowe SQLite i płatności symulowane. Nie weryfikują rzeczywistego PostgreSQL, produkcyjnych płatności, fizycznych telefonów ani pełnej sesji Chromium przez HTTP. Skrypt akceptacji nie podłącza Neon, domeny ani hostingu.

Uruchomienie: `python scripts/run_http_acceptance_suite.py`.
