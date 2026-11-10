# Weryfikacja 04 — zgodność adaptera PostgreSQL

Naprawiono generowanie `RETURNING id` w poleceniach INSERT zakończonych średnikiem. Wcześniej adapter doklejał klauzulę po średniku, powodując nieprawidłowy SQL; dodatkowo `lastrowid` nie rozpoznawał takiego zakończenia. Dodano cztery testy regresyjne.

**Ograniczenie:** testy adaptera są jednostkowe. W środowisku nie ma uruchomionego serwera PostgreSQL, więc nie potwierdzają działania wszystkich zapytań na rzeczywistej bazie. Przed wdrożeniem konieczne są testy PostgreSQL na odizolowanej instancji, migracje, równoległe zamówienia, rozliczenia i testy UI.

Strona publiczna i płatności produkcyjne pozostają bez zmian.
