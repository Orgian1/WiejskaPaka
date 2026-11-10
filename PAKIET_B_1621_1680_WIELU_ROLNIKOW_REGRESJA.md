# WiejskaPaka B/1621–B/1680 — zakupy od wielu rolników

Wykonane zmiany:
- Poprawiono limit 50 pozycji w `POST /cart/checkout-test`: limit obowiązuje dla przesyłki wybranego rolnika, a nie wszystkich pozycji koszyka innych rolników.
- Dodano regresję dwóch rolników i czterech produktów: dwa identyfikatory przesyłek, jedna opłata za przesyłkę, zachowanie pozostałych pozycji koszyka po pierwszym zakupie.
- Dodano regresję koszyka 52 pozycji: zakup jednego produktu u wybranego rolnika jest możliwy, a 51 pozycji innego rolnika pozostaje w koszyku.

Nie wdrożono jednoczesnego, atomowego zakupu u wszystkich rolników. Zakupy realizowane są osobno dla każdego rolnika.
Nie uruchamiano płatności rzeczywistych ani nie zmieniano konfiguracji Neon.

Testy: `python -m pytest -q tests/test_b1621_multiseller_shipping_regression.py` — 2 passed.
