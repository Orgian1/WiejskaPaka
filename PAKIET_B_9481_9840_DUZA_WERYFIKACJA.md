# WiejskaPaka B/9481–B/9840 — duża weryfikacja lokalna

## Faktycznie wykonane

- Zestaw akceptacyjny rzeczywistego HTTP: 4/4 scenariusze PASS (raport `RAPORT_HTTP_B_9481_9840.json`).
- 42 różne moduły testowe uruchomione **oddzielnie**, z osobną jednorazową bazą SQLite dla każdego modułu: 42 PASS, 0 FAIL.
- Raporty: `RAPORT_B_9481_9840_IZOLACJA.json` (15), `RAPORT_B_9481_9840_HTTP_PG_MOBILE.json` (11), `RAPORT_B_9481_9840_PG_MOBILE_RESZTA.json` (15), `RAPORT_B_9481_9840_OSTATNI.json` (1). Dwa raporty mają `complete=false` z powodu przerwania wykonywania całej zadanej listy przez limit czasu; wszystkie wpisane do nich wyniki są PASS, a pominięte moduły wykonano w następnym przebiegu.
- `node --check web/app.js` PASS; `python -m compileall -q backend scripts` PASS.
- Test Chromium -> lokalny HTTP wykonany ponownie: `BLOCKED` (ERR_BLOCKED_BY_ADMINISTRATOR); **niezaliczony**.
- Kontrola diagnostyczna: uruchomienie ośmiu testów pytest w jednym procesie i jednej bazie dało 2 błędy wynikające z pozostawionych rekordów z innych modułów. Te same osiem modułów osobno: 8/8 PASS. Nie zmieniano aplikacji, aby ukryć problem izolacji testów.

## Granice dowodów

Testy PostgreSQL w tym pakiecie obejmują preflight/guardy i moduły opcjonalne; **nie uruchomiono rzeczywistego serwera PostgreSQL**. Testy mobilne nie są testami na fizycznym telefonie. Płatności tylko testowe. Nie zmieniano Neon, hostingu, domeny ani konfiguracji prawdziwych płatności.

## Otwarte blokery

1. Odizolowany PostgreSQL i rzeczywiste transakcje.
2. Chromium przez prawdziwy HTTP bez blokady polityki środowiska.
3. Fizyczne urządzenia mobilne.
4. Pełny audyt bezpieczeństwa i zgodności prawnej przed produkcją.
