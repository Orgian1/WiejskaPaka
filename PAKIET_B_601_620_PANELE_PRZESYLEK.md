# B/601–B/620 — panele przesyłek

- API GET /shipments/farmer/mine: lista przesyłek wyłącznie zalogowanego rolnika, bez danych kontaktowych klientów.
- Panel klienta: historia przesyłek, liczba produktów, typ realizacji, opłata za przesyłkę i suma.
- Panel rolnika: analogiczna lista przesyłek jego gospodarstwa.
- Poprawka kompatybilności potwierdzania PIN z PostgreSQL: usunięto niepoprawne BEGIN IMMEDIATE w ścieżce przesyłek; realnego PostgreSQL nie testowano.
- Testy: test_b581_shipment_pin.py: 2 zaliczone; test_b561_shipment_links.py: 1 zaliczony (uruchomione oddzielnie); node --check web/dashboard.js bez błędów.

## Ograniczenia
- Panel dostawcy nadal pracuje na zamówieniach jednostkowych, a nie przesyłkach; wspólny PIN nie jest jeszcze obsługiwany przez jego interfejs.
- Migracja PostgreSQL wymaga osobnej weryfikacji; nie zmieniano Neon ani płatności produkcyjnych.
- Nie przeprowadzono pełnej regresji.
