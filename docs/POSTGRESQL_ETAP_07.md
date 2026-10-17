# Etap 7 backendu — PostgreSQL (tryb opt-in)

- Bez `DATABASE_URL` backend używa lokalnego SQLite, zachowując dotychczasowe testy.
- Po ustawieniu `DATABASE_URL` backend korzysta z `psycopg` i schematu PostgreSQL z etapu 6.
- Schemat należy utworzyć ręcznie przez `psql "$DATABASE_URL" -f database/postgres_schema.sql` (pusta baza). Tylko w lokalnym środowisku developerskim można użyć `WP_AUTO_INIT_POSTGRES=1`.
- Nie przechowuj adresu bazy ani haseł w repozytorium. Konto aplikacji powinno mieć ograniczone uprawnienia.
- Testy adaptera weryfikują tłumaczenie SQL, lecz **nie zastępują testów na działającym PostgreSQL**.
- Po ustawieniu `DATABASE_URL` uruchom `uvicorn backend.app:app --reload` i wykonaj pełne testy API na osobnej testowej bazie PostgreSQL.
- Migracja danych z SQLite to odrębna operacja: backup, migrator z etapu 6, kontrola liczności tabel i testy przed przełączeniem.
- Nie używaj równolegle obu baz do przyjmowania zamówień.

## Znane ograniczenia

- Zgodność schematu z działającą instancją PostgreSQL nie została jeszcze zweryfikowana w tej sesji.
- Backend nadal nie jest gotowy do publicznego wdrożenia: brak obsługi prawdziwych płatności, produkcyjnego zarządzania sekretami, limitów żądań na brzegu i audytu bezpieczeństwa.
