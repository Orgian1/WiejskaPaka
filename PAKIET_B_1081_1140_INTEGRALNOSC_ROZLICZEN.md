# B/1081–B/1140 — kontrola spójności pozycji zamówienia

Dodano do odczytowego raportu administratora `/admin/shipments/reconciliation` wykrywanie:
- `order_line_total_mismatch`: pojedyncza pozycja zamówienia nie spełnia `subtotal_grosze + delivery_grosze == total_grosze`, nawet jeśli błędy dwóch pozycji wzajemnie się znoszą w sumie przesyłki.
- `invalid_fulfillment`: nieznany rodzaj realizacji na przesyłce.
- `invalid_order_fulfillment`: nieznany rodzaj realizacji na pozycji zamówienia.

Test regresyjny obejmuje kompensujące się błędy kwot w dwóch zamówieniach. Nie ma automatycznej korekty danych. Nie zmieniano Neon ani rzeczywistych płatności.

Uruchomiono 9 plików testowych w osobnych procesach: 11 testów zaliczonych. Łączne uruchomienie tych plików w jednym procesie nadal powoduje kolizje izolacji baz testowych (4 niepowodzenia), ponieważ moduły testowe ustawiają `WIEJSKAPAKA_DB` przed importem aplikacji. Jest to problem infrastruktury testów wymagający osobnego refaktoringu.
