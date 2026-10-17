# WiejskaPaka — pakiet zbiorczy 53–65

## Zrealizowane (rzeczywisty zakres zmian)

- Wzmocniono adapter SQL SQLite → PostgreSQL: znaki `?` wewnątrz komentarzy `--`, zagnieżdżonych komentarzy `/* */`, identyfikatorów w cudzysłowach oraz literałów dolarowych PostgreSQL (`$$...$$`, `$tag$...$tag$`) nie są błędnie traktowane jako parametry.
- Obsłużono `BEGIN IMMEDIATE;` z końcowym średnikiem.
- Dodano 13 testów regresyjnych translatora, w tym sprawdzenie parametryzacji danych wejściowych.
- Wykonano pełny zestaw testów lokalnych na odizolowanej, świeżej bazie SQLite.

## Dlaczego to istotne

Dotychczasowy translator mógł zmienić treść SQL, jeśli znak `?` znajdował się w komentarzu lub literałach PostgreSQL. To błąd zgodności, który może powodować awarie po podłączeniu Neon. Poprawka nie zastępuje parametryzacji ani audytu zapytań dynamicznych.

## Ograniczenia i następne kroki

- Nie przeprowadzono testów na Neon. Nie zmieniano schematu ani uprawnień rzeczywistej bazy.
- RLS pozostaje wyłączony; polityki wymagają osobnego przeglądu, testów i bezpiecznego planu wdrożenia.
- Weryfikacja bezpieczeństwa całego API i przepływów finansowych nie jest zakończona.
- Rzeczywiste płatności, wypłaty i KSeF pozostają wyłączone.
- Przed wdrożeniem trzeba uruchomić integracyjne testy PostgreSQL w izolowanej bazie testowej z rolą aplikacyjną oraz sprawdzić uprawnienia i izolację transakcji.

Publiczna strona wiejskapaka.pl nie została zmieniona.
