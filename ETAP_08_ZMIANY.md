# WiejskaPaka — Neon etap 08

- Włączono w rzeczywistym endpointzie `GET /orders/{id}/location` centralną kontrolę dostępu kuriera.
- Kurier musi być przypisany do zamówienia z dostawą; adres znika po PIN (`pin_used=1`), potwierdzeniu (`confirmed_at`) lub zmianie statusu na zakończony.
- Sprawdzenie zamówienia i przypisania jest wykonywane jednym zapytaniem.
- Ujednolicono status dostawy w pomocniczym zapytaniu PostgreSQL: `w_drodze_testowo` zamiast nieużywanego `w_dostawie`.
- Zachowano dotychczasowe działanie: przypisany kurier może widzieć adres także przed oznaczeniem wysyłki, gdy zamówienie ma status `oczekuje_na_platnosc_testowa`. Wymaga to zaostrzenia przed produkcją.
- 1249 testów zaliczonych, 3 pominięte, 13 subtestów zaliczonych. Testy wykonano lokalnie, bez połączenia z Neon.

## Ważne ograniczenia
- RLS pozostaje wyłączony; konto aplikacji ma szerokie uprawnienia. Nie uruchamiać publicznie.
- Nie przetestowano prawdziwego połączenia PostgreSQL ani integracji płatności.
- Backend nadal używa lokalnej bazy SQLite domyślnie; Neon wymaga konfiguracji środowiska.
- Nie modyfikowano strony publicznej wiejskapaka.pl ani danych w Neon.
