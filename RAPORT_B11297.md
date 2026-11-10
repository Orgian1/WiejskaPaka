# WiejskaPaka — B/11297

## Zmiana
Rozszerzono bramę schematu PostgreSQL o trzy tabele wymagane podczas startu FastAPI: `inventory_reservations`, `order_purchase_records`, `pickup_point_coordinates`. Poprzedni preflight sprawdzał 11 tabel, lecz pomijał te trzy, więc mógł przepuścić niekompletny schemat i dopiero później przerwać start aplikacji. Obecnie sprawdza 14 tabel.

## Testy
`python -m pytest -q tests/test_b1129*.py tests/test_b11289_test_server_preflight.py` — **89 passed**. Dodano test zgodności z zapytaniami lifespan i testy braku każdej z trzech tabel.

## Ograniczenia
Testy z mockowanym połączeniem, bez prawdziwego serwera PostgreSQL. Nie przeprowadzono testów obciążeniowych ani wdrożenia produkcyjnego.
