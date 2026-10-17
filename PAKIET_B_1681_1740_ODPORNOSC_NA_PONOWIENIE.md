# B/1681–B/1740 — odporność koszyka na ponowienie żądania

- Endpoint `POST /cart/checkout-test` obsługuje opcjonalny nagłówek `Idempotency-Key` (8–128 znaków ASCII: litery, cyfry, `-_.:`).
- Ten sam użytkownik, klucz i dane zwracają zapisaną odpowiedź zamiast tworzyć drugą przesyłkę, drugi PIN lub ponownie odejmować magazyn.
- Ten sam klucz z innymi danymi: HTTP 409.
- Zapis klucza i utworzenie zamówienia odbywają się w jednej transakcji. Dla SQLite używany jest `BEGIN IMMEDIATE`.
- Lokalna tabela tworzona automatycznie. Dla PostgreSQL przygotowano migrację `database/upgrade_b1681_checkout_idempotency.sql` — NIE uruchamiano jej na Neon.
- Bez klucza zachowano dotychczasowe API. Klient powinien generować unikalny klucz na każdą próbę zatwierdzenia koszyka i używać tego samego przy ponowieniu po błędzie sieciowym.
- Wynik: 3 testy zaliczone (`test_b1681_checkout_idempotency.py`, `test_b1621_multiseller_shipping_regression.py`).
- Ograniczenia: nie sprawdzano rzeczywistego PostgreSQL, pełnej regresji ani UI; odpowiedź testowa zawiera PIN, dlatego tabela odpowiedzi wymaga ścisłych uprawnień i polityki retencji przed produkcją.
