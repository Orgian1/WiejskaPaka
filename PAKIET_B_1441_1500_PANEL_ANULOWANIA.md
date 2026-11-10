# B/1441–B/1500 — rozdzielenie anulowania w panelu klienta

W panelu klienta dodano dwa jawne działania: anulowanie przesyłki bez zarejestrowanej płatności oraz anulowanie przesyłki z zarejestrowanym zwrotem testowym. Druga operacja wymaga osobnego potwierdzenia, korzysta z `/shipments/{shipment_id}/cancel-paid-test`, wyświetla faktyczną kwotę z odpowiedzi serwera oraz informuje, że żadne środki nie są przelewane. Obsłużono ponowne wywołanie (already_processed).

Nie podłączono realnych płatności ani nie zmieniono konfiguracji Neon. UI nie rozstrzyga jeszcze z góry, która ścieżka jest dostępna — serwer egzekwuje warunki i zgłasza błędy. Do dalszej realizacji: statusy płatności w liście przesyłek, testy przeglądarkowe i pełna regresja.

Testy: `pytest tests/test_b1441_paid_cancel_panel.py tests/test_b1381_paid_shipment_cancel.py` (2 passed), `pytest tests/test_b1321_payment_cancel_guard.py` (1 passed), `pytest tests/test_b721_shipment_cancel.py` (1 passed), `node --check web/dashboard.js` (OK). Wspólny przebieg dwóch ostatnich testów wykazał kolizję danych testowych (1 failed), dlatego uruchomiono je osobno.
