# WiejskaPaka B/5821–B/5880 — diagnostyka uruchamiania testów HTTP

## Zmiany
- Naprawiono uruchamianie dwóch skryptów testowych bezpośrednio poleceniem `python scripts/...py` z dowolnego katalogu: wcześniej zgłaszały `ModuleNotFoundError: No module named 'scripts'`.
- Zachowano możliwość uruchamiania przez `python -m scripts...`.
- Dodano trzy testy regresyjne sprawdzające uruchamianie obu skryptów i izolację konfiguracji demonstracyjnej od danych PostgreSQL/Neon.

## Zweryfikowane wyniki (15 października 2026)
- `python -m unittest discover -s tests -p 'test_http_runner_entrypoints_b5821.py' -v`: **3/3 PASS**.
- `python scripts/check_real_http_loopback.py`: **16/16 PASS**, prawdziwe HTTP na loopback z jednorazową SQLite.
- `python scripts/check_chromium_real_http.py`: **BLOCKED, 0 zaliczonych**; środowisko blokuje nawigację Chromium na 127.0.0.1. Nie jest to test zaliczony.
- `python -m compileall -q backend scripts`: **PASS**.
- `node --check web/app.js`: **PASS**.

## Ograniczenia
Nie testowano rzeczywistego PostgreSQL, fizycznych telefonów ani prawdziwych płatności. Nie łączono się z Neon. Wyniki wcześniejszej regresji 211 modułów pochodzą z poprzedniego pakietu; po dodaniu testów nie uruchamiano ponownie całego zestawu.
