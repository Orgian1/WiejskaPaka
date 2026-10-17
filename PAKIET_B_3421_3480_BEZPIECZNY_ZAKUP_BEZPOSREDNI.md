# WiejskaPaka B/3421–3480 — zakup bezpośredni i przerwane połączenie

## Zmiana
Przycisk „Zamów testowo” zapisuje w sessionStorage znacznik nierozstrzygniętej operacji **przed** wysłaniem POST /orders. Znacznik znika wyłącznie po pomyślnej odpowiedzi dla tej samej sesji. Przy błędzie sieci, przełączeniu konta lub odświeżeniu strony ostrzeżenie pozostaje, a kolejne zakupy i modyfikacje koszyka są blokowane do ręcznej weryfikacji historii zamówień.

## Ograniczenia
Bezpośredni POST /orders nie ma jeszcze idempotencyjnego klucza po stronie serwera. Ręczne odblokowanie bez sprawdzenia historii może skutkować drugim zamówieniem. sessionStorage działa tylko w danej karcie i może być niedostępne. Nie są zapisywane tokeny, PIN-y ani adresy.

## Weryfikacja
`python -m pytest -q tests/test_b3361_direct_order_checkout_guard.py tests/test_b3301_refresh_checkout_guard.py tests/test_b3241_checkout_session_races.py` — 7 zaliczonych.
`node --check web/app.js` — OK.
`python -m compileall -q backend` — OK.

## Nadal do wykonania
Pełna regresja po zmianach, testy PostgreSQL, testy rzeczywistego HTTP i fizycznych urządzeń, audyt produkcyjny. Nie podłączono prawdziwych płatności ani Neon.
