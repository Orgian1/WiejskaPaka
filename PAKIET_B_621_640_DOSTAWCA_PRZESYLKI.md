# B/621–B/640 — obsługa przesyłki przez dostawcę (tryb testowy)

Nowe endpointy:
- POST /shipments/{shipment_id}/assign-courier-test — rolnik przypisuje jednego dostawcę wszystkim zamówieniom w przesyłce atomowo.
- POST /shipments/{shipment_id}/dispatch-test — rolnik wysyła wszystkie zamówienia w przesyłce atomowo; wymaga tego samego dostawcy dla wszystkich pozycji.
- GET /couriers/me/shipments — dostawca widzi wyłącznie kompletne przesyłki przypisane do siebie.

Dalszy odbiór: istniejący POST /shipments/{shipment_id}/confirm (jeden PIN).
Kwoty są w groszach; koszt dostawy pozostaje naliczany raz za przesyłkę.

Weryfikacja: `python -m pytest -q tests/test_b621_courier_shipments.py` (1 passed), `python -m pytest -q tests/test_b581_shipment_pin.py` (2 passed). Testy uruchomione osobno z uwagi na globalne zmienne środowiskowe w modułach testowych.

Ograniczenia: brak rzeczywistych płatności, integracji produkcyjnego PostgreSQL i pełnej regresji; obsługa nieudanych dostaw/zwrotów wymaga osobnej implementacji. Wcześniejsze endpointy dla pojedynczych zamówień nadal istnieją.
