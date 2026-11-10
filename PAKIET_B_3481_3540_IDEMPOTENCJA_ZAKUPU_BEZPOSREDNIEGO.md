# WiejskaPaka B/3481–B/3540 — idempotencja zakupu bezpośredniego

- `POST /orders` obsługuje opcjonalny nagłówek `Idempotency-Key` (12–100 znaków ASCII).
- Wykorzystuje istniejącą tabelę `checkout_idempotency`, z prefiksem `direct:` dla izolacji od zamówień koszykowych. Nie wymaga nowej migracji; istniejąca migracja B/1681 musi być zastosowana przed wdrożeniem na PostgreSQL.
- Ponowienie tego samego klucza i treści zwraca identyczną odpowiedź, bez tworzenia zamówienia i pomniejszania magazynu.
- Ten sam klucz z innymi danymi zwraca HTTP 409. Klucze są rozdzielone pomiędzy klientami.
- Interfejs generuje UUID dla każdego nowego zakupu bezpośredniego i wysyła nagłówek.
- Uwaga: interfejs nie przechowuje UUID po odświeżeniu strony ani nie umożliwia automatycznego wznowienia. Dotychczasowy znacznik ostrzegawczy nadal działa. To pozostaje do rozbudowy.
- Nie zmieniono produkcyjnych płatności, hostingu, domeny ani Neon.

## Testy

- `python -m pytest -q tests/test_b3481_direct_idempotency.py tests/test_b3361_direct_order_checkout_guard.py` — 5 zaliczonych.
- `python -m pytest -q tests/test_b1681_checkout_idempotency.py` — 1 zaliczony.
- Testy uruchomiono osobno, ponieważ część starszych modułów ustawia ścieżkę bazy przy imporcie.
- `python -m compileall -q backend` i `node --check web/app.js` — zaliczone.
- Nie wykonano pełnej regresji ani testu PostgreSQL.
