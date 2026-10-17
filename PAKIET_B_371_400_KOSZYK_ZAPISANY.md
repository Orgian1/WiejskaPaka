# B/371–B/400 — zapisany koszyk (zakres roboczy)

Dodano GET /cart/items, PUT /cart/items, DELETE /cart/items/{product_id} i DELETE /cart/items.
Dane koszyka są przypisane do zalogowanego klienta; limit 50 różnych produktów, ilość 1–1000, kontrola dostępności przy dodaniu. Koszyk nie rezerwuje towaru, nie zamraża ceny i nie tworzy zamówienia. Nie obsługuje rzeczywistych płatności.

SQLite: tabela tworzona lokalnie przy starcie. PostgreSQL: przed uruchomieniem endpointów należy ręcznie zastosować database/upgrade_b371_saved_cart.sql w środowisku testowym. Nie wykonano migracji w Neon.

Testy: python -m pytest -q tests/test_b371_saved_cart.py tests/test_b361_cart_quote.py

Do zrobienia: transakcyjny checkout wielu pozycji, walidacja punktów odbioru per sprzedawca, frontend, pełna regresja i testy integracyjne PostgreSQL.
