# WiejskaPaka — Pakiet B/18: profil rolnika i zmiana sesji

- `web/app.js`: żądania profilu i punktów odbioru mają licznik `farmerRequest` i kontrolę `sessionEpoch` oraz roli użytkownika przed każdą aktualizacją interfejsu.
- Zmiana konta lub wylogowanie unieważnia trwające odświeżanie panelu rolnika.
- Nieaktualne błędy poprzedniej sesji nie wyświetlają komunikatów.
- Usunięto zbędne żądanie `/products/mine` w `loadFarmer`, którego wynik nie był używany.
- `tests/test_web_farmer_profile_session.py`: trzy testy regresyjne.

## Weryfikacja
`node --check web/app.js` — OK.
Pełny zestaw testów z nowym plikiem SQLite: **2458 passed, 6 skipped, 16 subtests passed**.

Testy nie obejmują rzeczywistego telefonu ani PostgreSQL. Baza Neon, witryna wiejskapaka.pl i płatności produkcyjne nie były zmieniane.
