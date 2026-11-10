# B/1381–B/1440 — anulowanie opłaconej przesyłki (symulacja)

- Nowy endpoint `POST /shipments/{id}/cancel-paid-test` tylko dla właściciela przesyłki, przy `WP_ENABLE_TEST_PAYMENTS=1`.
- Atomowe anulowanie całej przesyłki w statusie oczekiwania na płatność, z symulowanym pełnym zwrotem opłaconych pozycji, odtworzeniem stanów magazynowych i dziennikiem zdarzeń.
- Ponowne wywołanie nie nalicza drugiego zwrotu i nie przywraca ponownie magazynu.
- Niedozwolone stany płatności i przesyłki są blokowane.
- Obsługa mieszanych płatności: zwracane są tylko pozycje rzeczywiście oznaczone jako opłacone w symulatorze.
- Kwoty pozostają w całkowitych groszach. Dostawa naliczana jest raz na przesyłkę.
- Nie podłączono operatora płatności ani Neon.

Testy: test_b1381_paid_shipment_cancel.py i test_b1321_payment_cancel_guard.py uruchomione osobno (wspólne uruchomienie koliduje przez istniejącą izolację globalnego modułu aplikacji).

Uwaga: to nie jest jeszcze pełny system prawnych odstąpień/reklamacji; nie obejmuje płatności rzeczywistych. Panel klienta wymaga integracji z nową ścieżką.
