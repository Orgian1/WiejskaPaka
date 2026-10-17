# WiejskaPaka B/5341–B/5400 — weryfikacja przeglądarki i ograniczeń środowiska

Data: 2026-10-15.

## Wykonane sprawdzenia

- `python -m scripts.check_mobile_offline`: Chromium offline 320×700, 390×844, 1280×800 — OK. Są to rzeczywiste renderowania przeglądarki z mockowanym API, **nie** testy serwera ani fizycznych telefonów.
- `python -m pytest -q tests/test_mobile_browser_runner.py tests/test_postgres_readiness.py tests/test_postgres_smoke_safety.py`: 10 zaliczonych testów.
- `python -m scripts.check_mobile_browser`: nie udało się wykonać testu połączonego z lokalnym serwerem, ponieważ Chromium zwrócił `net::ERR_BLOCKED_BY_ADMINISTRATOR` dla localhost. Testu nie wolno oznaczać jako zaliczony.
- Kontrola PostgreSQL nie została wykonana: w środowisku brak sterownika `psycopg`, brak jawnej zgody opt-in i brak lokalnej instancji PostgreSQL. Nie łączono się z Neon.

## Następne kroki

1. Wykonać test połączony Chromium + API na maszynie pozwalającej przeglądarce połączyć się z localhost.
2. Wykonać lokalne testy PostgreSQL na jednorazowej bazie testowej, bez modyfikowania produkcyjnego Neon.
3. Sprawdzić na fizycznych telefonach proces zakupowy, odbiór PIN, dostawę i zwroty testowe.
4. Audyt bezpieczeństwa i uprawnień przed wydaniem.

Regresja 211 modułów z poprzedniego pakietu dotyczy niezmienionego kodu aplikacji; w tym pakiecie nie zmieniano plików wykonywalnych aplikacji ani testów.
