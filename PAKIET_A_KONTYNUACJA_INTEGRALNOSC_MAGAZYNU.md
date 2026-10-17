# Pakiet A — integralność anulowania i stanów magazynowych

## Zmiana kodu
Endpoint `POST /orders/{order_id}/cancel-test` stosuje teraz warunkową zmianę statusu (`UPDATE ... WHERE status='oczekuje_na_platnosc_testowa'`) i sprawdza `rowcount == 1` **przed** przywróceniem stanu magazynowego. Dzięki temu nie przywraca zapasu, jeśli inna operacja zmieniła status zamówienia między odczytem i zapisem. Przywrócenie stanu i zapis zdarzenia pozostają w jednej transakcji.

## Testy
Dodano testy regresyjne anulowania, w tym powtórzenie żądania i weryfikację niezmienionego stanu magazynu. Uruchomiono całą lokalną suite na świeżej bazie SQLite: **2406 passed, 6 skipped, 16 subtests passed**.

## Ograniczenia
To **nie jest** potwierdzenie bezpieczeństwa współbieżności na PostgreSQL: testy integracyjne wymagają osobnego serwera PostgreSQL. RLS nie jest aktywowany, Neon nie był modyfikowany, rzeczywiste płatności pozostają wyłączone. Z projektu usunięto zapakowaną wcześniej bazę `backend/wiejskapaka.sqlite3` — archiwum nie powinno rozpowszechniać przypadkowych danych testowych.
