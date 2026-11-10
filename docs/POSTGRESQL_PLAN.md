# PostgreSQL — plan migracji (niezrealizowana)

> Aktualizacja 2026-10-16: poniżej znajduje się historyczny plan. Obecny kod
> ma opcjonalny adapter PostgreSQL, ręczne migracje i bramę natywnych testów.
> Domyślnym środowiskiem pozostaje lokalne SQLite. Natywna brama nie została
> zaliczona w tej sesji; sam adapter nie potwierdza poprawności PostgreSQL.
> Aktualne instrukcje: `docs/POSTGRESQL_TESTY_LOKALNE.md`. Nie podłączaj Neon
> ani bazy produkcyjnej.

Obecny backend używa SQLite. Nie wolno ustawiać DATABASE_URL do PostgreSQL i oczekiwać działania: kod korzysta bezpośrednio z sqlite3.

## Przed migracją
1. Wyodrębnić warstwę repozytoriów / ORM (np. SQLAlchemy 2) i transakcje.
2. Przygotować migracje Alembic z tabelami users, sessions, products, orders, farmer_profiles, pickup_points, order_locations.
3. Wymusić klucze obce, ograniczenia kwot w groszach i blokowanie wierszy produktów w transakcji.
4. Wykonać testy równoległych zakupów, izolacji użytkowników, anulowania i PIN.
5. Uruchomić PostgreSQL na osobnym środowisku testowym, wykonać kopie zapasowe i próbne odtworzenie.

Nie publikować API do internetu przed ukończeniem zabezpieczeń i migracji.
