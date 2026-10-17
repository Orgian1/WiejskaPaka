# B/11314 — wzmocnienie kontroli pustej bazy PostgreSQL

- Preflight przed migracjami uruchamia `SET TRANSACTION READ ONLY` przed zapytaniami diagnostycznymi.
- Kontrola obiektów obejmuje wszystkie schematy użytkownika, nie tylko `public`, z wyłączeniem wewnętrznych schematów PostgreSQL.
- Uzupełniono testy kolejności zapytań i zakresu kontroli.
- Wynik: 201 testów zakończonych powodzeniem (wybrany zestaw testów ostatnich etapów).
- Brak działającego PostgreSQL w tym środowisku; nie wykonano rzeczywistych migracji ani testów obciążeniowych.
- Kolejny krok: uruchomienie PostgreSQL w izolowanym środowisku, wykonanie migracji i test aplikacji. Zakup VPS nie jest jeszcze niezbędny, jeśli można uruchomić lokalną bazę.
