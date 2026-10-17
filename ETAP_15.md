# Etap 15 — projekt polityk RLS (TYLKO DO PRZEGLĄDU)

Dodano `backend/neon_rls_policy_plan.py` z kandydatami predykatów SELECT dla sześciu tabel: `users`, `sessions`, `orders`, `order_locations`, `delivery_assignments`, `seller_compliance`. Funkcja `review_select_policies()` **zwraca tekst** — nie uruchamia SQL. Nie ma migracji aktywującej RLS.

**NIE uruchamiać wygenerowanych polityk na Neon.** To szkic, nie kompletny zestaw polityk. Szczególnie ważne:

- Logowanie wymaga odczytu `sessions` zanim można ustawić identyfikator aktora; polityka na `sessions` mogłaby zablokować logowanie.
- Zagnieżdżone odwołania `orders` ↔ `delivery_assignments` mogą powodować rekurencję RLS; trzeba zaprojektować bezpieczny model uprawnień i przetestować go na osobnym PostgreSQL.
- RLS ogranicza **wiersze**, a nie kolumny. Nie wolno zwracać `pin_hash`, adresów czy innych danych wrażliwych poprzez `SELECT *`.
- Brakuje zasad zapisu, operacji administracyjnych, migracji i zadań systemowych.
- Custom GUC ustawiony przez konto aplikacji nie jest zabezpieczeniem przed przejęciem tego konta; API nadal musi weryfikować sesje i autoryzację.
- Stan aplikacji nie jest gotowy do publicznego wdrożenia. Płatności są testowe.

Następny etap: zinwentaryzować rzeczywiste zapytania i role, usunąć potencjalną rekurencję, przygotować odizolowane testy PostgreSQL przed jakimkolwiek wdrożeniem.
