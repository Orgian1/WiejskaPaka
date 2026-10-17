# Pakiet 2/5 — panele użytkowników (wersja testowa)

Dodano do istniejącego interfejsu role: klient (zakupy, historia statusów), rolnik (zamówienia, przypisywanie dostawcy, podgląd rozliczeń testowych), dostawca (lista dostaw, zmiana statusu i potwierdzenie PIN) oraz administrator (podgląd raportu finansowego testowego). Wspólna sekcja powiadomień umożliwia oznaczanie jako przeczytane.

Frontend korzysta z już istniejących endpointów API i nie przechowuje tokenów w localStorage. Wartości są wyświetlane przez textContent, bez wstawiania danych użytkowników przez innerHTML.

Ograniczenia: panel jest nadal demonstracyjny; dostępność przycisków zależy od statusu zamówienia i flag testowych; brak pełnego UX procesu zamówienia, automatycznego harmonogramu, płatności i testów E2E w przeglądarce. Backend sprawdza uprawnienia niezależnie od ukrywania paneli.
