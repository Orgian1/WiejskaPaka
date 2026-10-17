# Etap 14 — audyt gotowości RLS

Dodano `backend/neon_rls_preflight.py` oraz testy jednostkowe.
Audyt jest wyłącznie odczytowy i obejmuje sześć tabel wrażliwych.
Nie włącza RLS i nie modyfikuje bazy Neon.

**Uwaga bezpieczeństwa:** konto aplikacji posiada obecnie SELECT/INSERT/UPDATE/DELETE
na wszystkich tabelach; RLS jest wyłączony. Nie wolno udostępniać backendu publicznie.
Samo ustawienie `wiejskapaka.actor_id` nie jest granicą zaufania dla konta SQL:
każdy, kto uzyska możliwość wykonywania dowolnego SQL na tym koncie, może ustawić
własny identyfikator. Konieczne są parametryzowane zapytania, brak arbitralnego SQL,
weryfikacja sesji oraz testy rzeczywistego połączenia i polityk.

Przed wdrożeniem: sprawdzić kompatybilność istniejących endpointów, zaprojektować
polityki RLS, role migracyjne i aplikacyjne, operacje systemowe oraz transakcje.
Nie wpisywać danych dostępowych do kodu ani do rozmowy.
