# Pakiet B/351–B/360 — wyszukiwanie produktów (lokalne API)

Dodano `GET /catalog/search` z parametrami `q`, `min_price_grosze`, `max_price_grosze`, `limit` i `offset`.
Odpowiedź zawiera `items`, `total`, `limit`, `offset`. Tylko dostępne produkty (`stock > 0`).
Wyszukiwanie jest parametryzowane, a znaki `%` i `_` traktowane dosłownie.
Limit wynosi maksymalnie 100 produktów na stronę. Ceny to liczby całkowite w groszach.
Nie dodawano płatności, migracji Neon ani zmian domeny. Wyszukiwarka jest na poziomie API; widok UI wymaga osobnej pracy.
Test: `python -m pytest -q tests/test_b351_catalog_search.py tests/test_b321_farmer_product_edit.py tests/test_b341_product_details.py`.
