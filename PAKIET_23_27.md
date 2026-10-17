# WiejskaPaka — pakiet 23–27 (zbiorczy)

## Zrealizowane
- Wspólna walidacja dat wygaśnięcia sesji PostgreSQL (timestamptz oraz ISO 8601), z odrzucaniem dat bez strefy i niepoprawnych identyfikatorów.
- Ujednolicona kontrola aktualnej roli z tabeli users wewnątrz zweryfikowanej transakcji PostgreSQL.
- Integracja tej kontroli w GET /orders/me i GET /couriers/me/active-addresses dla trybu PostgreSQL.
- Testy przypadków granicznych, nieważnych sesji, nieznanych ról i parametryzacji zapytania.
- Pełny lokalny zestaw testów: 1294 zaliczone, 3 pominięte, 16 podtestów zaliczonych.

## Nadal do wykonania przed uruchomieniem
- Inne endpointy zapisujące i odczytujące dane nadal używają starszego mechanizmu; wymagają migracji do transakcji ze zweryfikowaną sesją.
- RLS pozostaje wyłączony; projekt polityk wymaga przeglądu i testów PostgreSQL.
- Nie przeprowadzono połączenia z prawdziwą bazą Neon ani testów produkcyjnych.
- Płatności produkcyjne są wyłączone. Nie zmieniano publicznej witryny.

Nie uruchamiać SQL RLS na Neon na podstawie samego tego pakietu.
