# B/1501–B/1560 — historia finansowa klienta (tryb testowy)

Nowy odczyt `GET /shipments/{shipment_id}/financial-history-test` udostępnia wyłącznie właścicielowi przesyłki podsumowanie kwot produktów, pojedynczego kosztu dostawy, symulowanych zwrotów, stanów płatności oraz historię statusów zamówień. Zwraca 404 dla cudzych przesyłek; nie zawiera adresu, numeru telefonu, PIN, identyfikatorów zdarzeń płatniczych ani tokenów.

Wdrożenie obejmuje API i test automatyczny. Nie dodano jeszcze graficznej prezentacji historii w panelu klienta. Nie uruchamiano testów Neon/PostgreSQL ani pełnej regresji. Płatności i zwroty pozostają symulacją.

Testy: `python -m pytest -q tests/test_b1501_financial_history.py` (1 passed); `python -m pytest -q tests/test_b1381_paid_shipment_cancel.py` (1 passed); `python -m compileall -q backend` (OK).
