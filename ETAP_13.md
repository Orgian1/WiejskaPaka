# Etap 13 — spójność polityki dostępu do adresów

Poprawiono pięć nieaktualnych testów regresyjnych, które oczekiwały ujawniania adresów dostaw przed wysłaniem zamówienia albo rolnikowi. Zasady: kurier widzi adres tylko gdy jest przypisany, zamówienie ma status `w_drodze_testowo`, PIN nie został użyty i nie ma daty potwierdzenia. Rolnik nie otrzymuje adresu klienta przez `/orders/{id}/location`; klient widzi swoje zamówienie. Testy sprawdzają zachowanie istniejącego API, bez zmian w publicznej stronie.

Wynik lokalny: `python -m pytest -q --disable-warnings` — **1265 passed, 3 skipped, 16 subtests passed**. Trzy pominięte testy dotyczą m.in. integracji z żywym PostgreSQL; nie przeprowadzono testu na bazie Neon użytkownika.

Uwaga: nie włączono RLS i nie wdrożono produkcyjnych płatności. Nadal konieczna jest integracja PostgreSQL, przegląd wszystkich ścieżek dostępu do danych i testy integracyjne. Zmiana obejmuje korektę oczekiwań testowych zgodnie z aktualnym kodem bezpieczeństwa, nie nową implementację RLS.
