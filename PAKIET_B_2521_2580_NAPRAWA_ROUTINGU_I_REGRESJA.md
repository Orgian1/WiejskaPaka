# WiejskaPaka — B/2521–B/2580

## Naprawa rzeczywistego błędu

W szerszej regresji wykryto błąd HTTP 422 dla `GET /products/mine`.
Przyczyną była kolejność tras FastAPI: `/products/{product_id}` zdefiniowano przed `/products/mine`, przez co `mine` traktowano jako identyfikator liczbowy.
Przeniesiono statyczną trasę `/products/mine` przed trasę parametryczną.
W teście magazynowym dodano jawne sprawdzenie kodu odpowiedzi i treści błędu.

## Wykonane kontrole

- Grupa 5: 12/12 modułów PASS.
- Grupa 6: 12/12 modułów PASS (wznowienie po przerwaniu).
- Grupa 7: 12/12 modułów PASS po poprawce.
- Dodatkowo testy `test_inventory_lifecycle_package.py` i `test_stage2.py`: 4 PASS.
- Kompilacja backendu: PASS.

Wyniki dotyczą wyłącznie wskazanych modułów na lokalnym SQLite; nie potwierdzają pełnej regresji ani testów PostgreSQL/przeglądarki.
Nie zmieniano Neon, produkcyjnych płatności, domeny ani hostingu.
