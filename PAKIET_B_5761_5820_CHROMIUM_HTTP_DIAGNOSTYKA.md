# WiejskaPaka B/5761–5820 — diagnostyka Chromium i HTTP

Data: 2026-10-15. Środowisko lokalne, jednorazowa baza SQLite.

## Wyniki faktycznie wykonane
- `python -m scripts.check_real_http_loopback`: **PASS, 16/16** kontroli rzeczywistego HTTP do lokalnego Uvicorn.
- `python -m scripts.check_chromium_real_http`: **BLOCKED, 0 zaliczonych**. Polityka środowiska blokuje nawigację Chromium do 127.0.0.1; nie jest to potwierdzenie usterki aplikacji ani zaliczenie testu.
- `python -m compileall -q backend scripts`: **PASS**.
- `node --check web/app.js`: **PASS**.

## Sposób uruchomienia
Uruchamiać skrypty jako moduły z katalogu projektu (`python -m scripts.check_chromium_real_http`), a nie przez bezpośrednie wywołanie pliku, gdyż import `scripts.run_phone_demo` wymaga katalogu głównego na ścieżce modułów.

## Pozostałe kontrole
Test Chromium→TCP→FastAPI wymaga środowiska bez blokady loopback; osobna baza PostgreSQL, fizyczne urządzenia i pełny audyt bezpieczeństwa nadal nie są potwierdzone. Nie korzystano z Neon, płatności rzeczywistych, hostingu ani domeny.
