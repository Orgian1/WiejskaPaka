# WiejskaPaka B/5941–B/6000 — zakup, dostawa i zwrot przez prawdziwe HTTP

## Wykonano
- Nowy skrypt `scripts/check_http_checkout_e2e.py` uruchamia lokalny Uvicorn na 127.0.0.1 z jednorazową bazą SQLite i **włączonymi wyłącznie w tym procesie płatnościami testowymi**.
- 28 zaliczonych kontroli obejmuje rejestrację czterech kont testowych, logowanie, utworzenie produktu, zamówienie z dostawą, opłatę 501 gr naliczoną jeden raz, ograniczenia dostępu do adresu, przypisanie kuriera, błędny i poprawny PIN, odebranie dostępu do adresu po potwierdzeniu oraz pełny zwrot 850 gr po nieudanej dostawie (349 gr towar + 501 gr dostawa).
- Wyniki zapisane w `HTTP_CHECKOUT_E2E_REPORT.json`.
- Dodano test regresyjny `tests/test_http_checkout_e2e_b5941.py`.
- `python -m pytest -q tests/test_http_checkout_e2e_b5941.py tests/test_http_runner_entrypoints_b5821.py`: 4 zaliczone.
- `node --check web/app.js` i `python -m compileall -q backend scripts`: zaliczone.

## Ograniczenia
- Przeglądarka Chromium nadal nie może wejść na lokalny serwer z powodu polityki środowiska (status BLOCKED). Nowy test korzysta z prawdziwego HTTP przez httpx, **nie z Chromium**.
- PostgreSQL nie był uruchamiany; konfiguracja Neon, hosting, domena i płatności produkcyjne pozostały nietknięte.
- Test nie obejmuje całej macierzy wieloproduktowych przesyłek; istnieją osobne testy modułowe tej logiki.
