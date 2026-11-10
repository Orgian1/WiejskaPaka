# WiejskaPaka — B/1681–B/1740: zabezpieczenie przed podwójnym zamówieniem

Zaimplementowano opcjonalny nagłówek `Idempotency-Key` dla `POST /cart/checkout-test`.
- Klucz 12–100 znaków (litery ASCII, cyfry, `_` i `-`).
- Pierwszy zakup tworzy przesyłkę i zapisuje odpowiedź w tej samej transakcji co zamówienia, magazyn i koszyk.
- Powtórzenie z tym samym kluczem i identycznym żądaniem zwraca pierwotny wynik bez tworzenia nowego zamówienia.
- Użycie klucza z innymi danymi daje HTTP 409.
- Klucze są rozdzielone według konta klienta.
- Bez klucza zachowane jest dotychczasowe działanie (nie chroni przed podwójnym kliknięciem).
- Odpowiedź zawiera testowy PIN, więc nie należy przechowywać ani logować jej poza bezpiecznym środowiskiem testowym. Przed produkcją trzeba zmienić sposób przekazywania PIN.
- SQLite: tabela tworzona lokalnie. PostgreSQL: plik `database/upgrade_b1681_checkout_idempotency.sql` do ręcznej oceny i migracji; **nie wykonano migracji Neon**.

Testy uruchomione osobno:
- test_b1681_checkout_idempotency.py — 1 passed
- test_b1621_multiseller_shipping_regression.py — 2 passed
- test_b1381_paid_shipment_cancel.py — 1 passed
- test_b581_shipment_pin.py — 2 passed

Nie wykonano pełnej regresji ani testów na PostgreSQL. Nie podłączono rzeczywistych płatności.
