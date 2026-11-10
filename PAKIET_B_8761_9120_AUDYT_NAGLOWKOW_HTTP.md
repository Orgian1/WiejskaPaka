# WiejskaPaka — pakiet B/8761–B/9120

## Wykonane zmiany
- Dodano `scripts/audit_http_response_headers.py`: audyt nagłówków bezpieczeństwa na **rzeczywistym lokalnym HTTP** (Uvicorn/FastAPI) z odizolowaną bazą SQLite.
- Dodano `tests/test_b8761_http_response_headers.py`: automatyczny test regresyjny.
- Dodano `HTTP_HEADERS_AUDIT_B8761.json`: szczegółowe wyniki 13 kontroli.

## Wyniki uruchomione w tym pakiecie
- 13/13 kontroli nagłówków i zasad cache: PASS, obejmujących statusy 200, 201, 401, 403, 404, 422.
- `python -m pytest -q tests/test_b8761_http_response_headers.py`: 1 passed.
- `python scripts/run_http_acceptance_suite.py`: 4/4 zestawy PASS.
- `node --check web/app.js`: PASS.
- `python -m compileall -q backend scripts`: PASS.
- `python scripts/check_chromium_real_http.py`: BLOCKED (polityka środowiska blokuje Chromium -> localhost); niezaliczone.

## Granice weryfikacji
- Nie uruchamiano serwera PostgreSQL ani testów na fizycznych telefonach.
- Nie wykonywano pełnego audytu bezpieczeństwa lub zgodności prawnej.
- Brak podłączenia Neon, płatności produkcyjnych, hostingu i domeny.
- To nie jest potwierdzenie gotowości produkcyjnej.
