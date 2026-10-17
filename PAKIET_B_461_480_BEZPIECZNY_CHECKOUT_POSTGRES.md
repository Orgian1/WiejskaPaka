# B/461–B/480: poprawa współbieżności checkout PostgreSQL

Wprowadzono dwie poprawki w `/cart/checkout-test`:
- W trybie PostgreSQL nie jest uruchamiana ręczna instrukcja `BEGIN` wewnątrz istniejącej transakcji z `postgres_verified_db`.
- Odczyt pozycji koszyka i produktów blokuje rekordy `FOR UPDATE OF c,p` na czas sprawdzenia cen, stanów i tworzenia zamówień. SQLite zachowuje `BEGIN IMMEDIATE`.

Dodano dwa testy kontraktowe, uruchomiono również testy checkout i zapisanego koszyka: 5/5 zaliczonych. Sprawdzono składnię backendu. Nie wykonywano testów na prawdziwej instancji PostgreSQL/Neon ani całej regresji. Pozostałe endpointy i migracje wymagają osobnego audytu. Nie włączono płatności produkcyjnych.
