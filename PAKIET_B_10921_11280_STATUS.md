# WiejskaPaka — rozpoczęta paczka B/10921–B/11280

## Rzeczywiście wykonane
- Dodano niezależny audyt blokady logowania przez rzeczywisty HTTP, na serwerze Uvicorn i jednorazowej bazie SQLite.
- Sprawdzono pięć błędnych prób, blokadę poprawnego hasła po przekroczeniu limitu, izolację kont, nieznane konto i normalizację adresu e-mail: **13/13 kontroli PASS**.
- Dodano test regresyjny pytest; uruchomiono go razem z poprzednim testem sesji: **2/2 PASS**.
- Uruchomiono `compileall` oraz `node --check` bez zgłoszonych błędów.
- Uruchomiono również pełną regresję pytest, lecz proces przekroczył limit czasu środowiska; **nie wolno uznawać pełnej regresji za zaliczoną**.

## Pozostałe bramy
- Brak rzeczywistego PostgreSQL; brak testów Chromium i fizycznych telefonów.
- Brak końcowego audytu bezpieczeństwa i kontroli prawnej.
- Paczka B/10921–B/11280 jest **w toku**, nie należy traktować wszystkich 360 punktów jako zakończonych.
- Brak płatności produkcyjnych, Neon, domeny i hostingu.
