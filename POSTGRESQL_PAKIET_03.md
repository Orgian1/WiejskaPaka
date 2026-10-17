# PostgreSQL — pakiet 03: ochrona testu odczytowego

## Wprowadzone zmiany
- Test `tests/test_postgres_live_opt_in.py` weryfikuje docelowy DSN za pomocą `require_disposable_postgres()` **przed** otwarciem połączenia.
- Odrzuca bazę o nazwie innej niż `*_test` lub `wp_test_*`, a zdalny serwer wymaga jawnej zgody środowiskowej. To dodatkowa ochrona przed pomyłką, nie gwarancja bezpieczeństwa.
- Test wymusza `SET TRANSACTION READ ONLY` przed zapytaniami diagnostycznymi.
- Usunięto błędne założenie, że raport audytu zawsze musi zwracać `ready_for_public_launch=False`; test kontroluje teraz format wyników. Faktyczna gotowość wymaga osobnego przeglądu.
- Dodano 4 testy regresyjne, w tym potwierdzenie braku próby połączenia z niezatwierdzoną bazą.

## Wyniki
- Pełny lokalny zestaw: **2396 passed, 4 skipped, 16 subtests passed**.
- Nie uruchomiono rzeczywistego PostgreSQL ani Neon. Testy integracyjne PostgreSQL są pominięte bez osobnej bazy testowej.

## Pozostałe blokery
- Testy na odizolowanym serwerze PostgreSQL z prawdziwymi transakcjami i równoległością.
- Kompleksowy przegląd uprawnień, RLS i skutków użycia wspólnej roli bazy.
- Weryfikacja scenariuszy API, przegląd prawny i uruchomienie płatności dopiero po ukończeniu aplikacji.
- Nie zmieniono publicznej strony, bazy Neon ani konfiguracji prawdziwych płatności.
