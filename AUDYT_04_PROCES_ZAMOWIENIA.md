# Audyt 04 — pełny proces zamówienia (lokalny tryb testowy)

- Test end-to-end: utworzenie dostawy, przypisanie kuriera, brak dostępu do adresu przed rozpoczęciem, rozpoczęcie, dostęp wyłącznie przypisanego kuriera, potwierdzenie PIN, utrata dostępu do adresu i blokada ponownego potwierdzenia.
- Test limitu 5 nieudanych prób PIN i blokady także przy późniejszym podaniu prawidłowego kodu.
- Dodatkowe wzmocnienie: status wymagany przy potwierdzeniu jest powiązany z rodzajem realizacji (odbiór = gotowe_do_odbioru_testowo; dostawa = w_drodze_testowo).
- Pełny zestaw lokalny: 2368 passed, 4 skipped, 16 subtests passed.

## Nierozwiązane przed produkcją
- Brak testu integracyjnego z rzeczywistą bazą PostgreSQL/Neon.
- RLS jest wyłączony; uprawnienia i polityki wymagają niezależnej weryfikacji.
- Płatności, wypłaty, zwroty i dokumenty są symulacjami. Test procesu nie oznacza, że rzeczywista płatność została pobrana.
- Wymagane dodatkowe testy równoległości i migracji na PostgreSQL oraz przegląd prawny.
- Nie wprowadzono żadnych zmian w bazie Neon ani na wiejskapaka.pl.
