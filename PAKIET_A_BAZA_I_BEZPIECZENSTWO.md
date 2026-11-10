# Pakiet A — baza danych i bezpieczeństwo (stan na 14.10.2026)

## Wykonane
- Dodano diagnostykę tylko do odczytu `backend/postgres_readiness.py` dla sześciu tabel wrażliwych.
- Raport rozróżnia brak tabeli, wyłączony RLS, liczbę polityk i prawo SELECT bieżącej roli.
- Raport **nigdy nie stwierdza gotowości produkcyjnej** na podstawie samych flag RLS.
- Dodano testy z fałszywym połączeniem, bez haseł i połączenia z Neon.

## Blokery i ograniczenia
1. Brak uruchomionego odizolowanego PostgreSQL w tym środowisku — testy integracyjne nadal pomijane.
2. Nie wykonano testu połączenia z Neon, nie zmieniano żadnych tabel ani uprawnień.
3. RLS w Neon jest wyłączony. Projekt polityk wymaga osobnego przeglądu i testów z rolą o minimalnych uprawnieniach.
4. Wspólny login aplikacji z możliwością ustawiania własnych GUC nie daje samodzielnej granicy bezpieczeństwa RLS; konieczne są autoryzacja aplikacyjna i analiza modelu ról.
5. Włączenie RLS bez sprawdzenia logowania, uprawnień i transakcji może zablokować aplikację.
6. Wyniki lokalnych testów nie są dowodem bezpieczeństwa produkcyjnego.

## Następny warunek ukończenia pakietu A
Przeprowadzić testy na *osobnej, jednorazowej bazie PostgreSQL*, zweryfikować migracje, sesje, uprawnienia i przepływy oraz usunąć wykryte błędy. Dopiero potem planować zmiany w Neon. Publiczna witryna i płatności pozostają nietknięte.
