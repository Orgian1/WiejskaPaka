# WiejskaPaka — B/8401–B/8760

## Wykonano
- Rozszerzono test rzeczywistego HTTP koszyka wielu rolników o kontrolę dostępu do szczegółów przesyłek, historii finansowej, list przesyłek klienta i rolnika.
- Sprawdzono izolację przesyłek dwóch rolników oraz obcego klienta.
- Dodano 2 testy regresyjne kontraktu audytu.

## Potwierdzone wyniki
- Test wielosprzedawcowy: **55/55** kontroli, PASS.
- Testy regresyjne: **3/3**, PASS (w tym jeden wcześniejszy test prywatności).
- Zbiorczy test akceptacyjny HTTP: **4/4** zestawy PASS.
- `node --check web/app.js` oraz `python -m compileall -q backend scripts`: PASS.

## Ograniczenia
- Testy wykorzystują wyłącznie jednorazową bazę SQLite i symulację płatności.
- Nie testowano rzeczywistego PostgreSQL ani Neon.
- Nie przeprowadzono testu Chromium przez HTTP ani testów na fizycznych telefonach.
- Testy uprawnień są punktowe; nie stanowią pełnego audytu bezpieczeństwa.
- Nie zmieniono hostingu, domeny ani płatności produkcyjnych.
