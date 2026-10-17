# B/3541–B/3600 — sprawdzenie zakupu bezpośredniego po odświeżeniu

- Endpoint `GET /orders/idempotency-status/{request_key}` sprawdza wyłącznie własne żądanie klienta i zwraca jedynie `completed` oraz identyfikator zamówienia; nigdy PIN.
- Interfejs przechowuje w sessionStorage identyfikator bezpośredniej operacji (nie token, adres, PIN). Po ponownym zalogowaniu użytkownik może sprawdzić, czy zamówienie zostało zapisane.
- Nieznany identyfikator NIE odblokowuje koszyka automatycznie: opóźnione żądanie może być w trakcie przetwarzania.
- Użytkownik może nadal świadomie odblokować koszyk po sprawdzeniu historii zamówień.
- Ograniczenie: zapis sessionStorage jest zależny od dostępności pamięci przeglądarki i pozostaje lokalny dla karty. Pełna regresja i testy mobilne/PG są nadal wymagane.

Kontrole: `pytest -q tests/test_b3541_direct_reconciliation.py` (1 passed), `pytest -q tests/test_b3481_direct_idempotency.py tests/test_b3361_direct_order_checkout_guard.py` (5 passed), `node --check web/app.js`, `python -m compileall -q backend`.
