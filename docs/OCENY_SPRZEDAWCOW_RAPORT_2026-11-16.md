# Oceny sprzedawców — raport końcowy

[PR #64](https://github.com/Orgian1/WiejskaPaka/pull/64) bazuje na #63, zawierającym wcześniejsze zmiany #62. Testowany kod: `a52efd992b81e4a392d3ece2ca2594c6c19abf1e`. Po testach zmieniono wyłącznie dokumentację wyników. Nie zmieniano VPS, produkcyjnej bazy ani rzeczywistych płatności PayU.

## Dostarczone działanie

Kupujący w historii własnych odebranych zamówień wybiera 1–5 gwiazdek i naciska „Zapisz ocenę”. Zamówienie musi mieć status odebrane, wykorzystany PIN i potwierdzenie odbioru. Zapisana ocena jest widoczna także po ponownym logowaniu. Pod sprzedawcą klient widzi średnią i licznik ocen; informacje występują przy ofertach, w wyszukiwarce sprzedawców, historii odebranego zakupu i panelu sprzedawcy. Zero ocen oznacza brak średniej, nie ocenę zero.

Każde zamówienie ma najwyżej jedną ocenę. Ponowienie tego samego zapisu jest idempotentne, a zmiana raz zapisanej oceny jest odrzucana. Blokada zamówienia w transakcji i klucz główny order_id chronią przed równoczesnym głosowaniem. Cudze, nieodebrane i anulowane zamówienia nie pozwalają wystawić oceny. W przesyłce obejmującej kilka zamówień można ocenić każde odebrane zamówienie, nie każdą sztukę towaru.

Nie zmieniono zasad PIN-u, prowizji, portfela, wypłat, rozliczeń w groszach ani zwrotów. Dane starej listy zamówień nie zostały rozszerzone o prywatne pola; nowy endpoint własnej oceny dostarcza wyłącznie ID zamówienia, ID sprzedawcy i gwiazdki.

## Bezpieczeństwo

Publiczny endpoint zwraca wyłącznie średnią i licznik dla sprzedawcy. Nie ujawnia kupujących, pojedynczych ocen innych klientów, adresów, PIN-ów ani tokenów. Odczyt i zapis własnej oceny wymagają ważnej sesji klienta. Zapisy ponownie uwierzytelniają użytkownika w tej samej transakcji, a relacja kupujący–zamówienie–sprzedawca pochodzi z bazy, nie z żądania. Gwiazdki są ścisłą liczbą całkowitą 1–5; dodatkowe parametry są zabronione.

Tabela ma ENABLE/FORCE RLS i pięć jawnych polityk. Wykonawca gateway nie ma UPDATE/DELETE, a SQLite używa blokujących triggerów. Właścicielska polityka ocen nie korzysta z wyjątków bootstrapu sesji: kontekst auth bez tożsamości nie może czytać ani tworzyć ocen. GUC actor_id/rola nie nadaje tożsamości. Publiczny agregat COUNT/SUM ma osobną, wąską funkcję guard z ustalonym search_path. Nie przyznano aplikacji własności tabeli ani uprawnień administracyjnych.

Audyt tras oznacza jako publiczny wyłącznie dokładny GET agregatu. Inne metody i prywatne endpointy ocen pozostają uwierzytelniane; test kontraktowy pilnuje granicy tego wyjątku.

## Wyniki

| Zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Pełna regresja: 401 modułów / 5080 przypadków | 4974 | 0 | 106 |
| Te same unikalne przypadki po uzupełnieniu testów opcjonalnych | **5078** | **0** | **2** |
| Rzeczywisty PostgreSQL 16.2 / FORCE RLS: całe API i próby SQL | 168 | 0 | 0 |
| PostgreSQL przed migracją RLS i sondy środowiska | 97 | 0 | 0 |
| Końcowy zestaw celowany: oceny, SQL, manifest, kontrakty UI i audyt publicznych tras | 48 | 0 | 0 |
| Rozszerzone role Chromium: 12 scenariuszy z mock API | 4 | 0 | 0 |

Zestawy nakładają się i nie należy sumować ich liczników. Zestaw celowany obejmuje rozbudowany scenariusz HTTP, dwa scenariusze Chromium (320/1280 px), 15 prób SQL/RLS oraz testy manifestu, ładowania skryptów i klasyfikacji tras. Pełny odbiór PostgreSQL obejmuje również rzeczywisty przebieg zakupu, potwierdzenia PIN-em i wystawienia ocen z różnych kont, wspólną średnią, konkurencyjne zapisy i brak ujawnienia autorów.

W realnym odbiorze TCP HTTP potwierdzono odpowiedź **2xx dla wszystkich 149/149 tras API**, w tym trzech nowych tras ocen. Dodatkowy scenariusz Chromium → backend FastAPI przeszedł 88 żądań (transport in-process), obejmując odbiór, izolację dostawcy, PIN i idempotentny zwrot. `pip check` i `git diff --check`: PASS. Istniejące ostrzeżenie deprecjacyjne TestClient/httpx nie powoduje błędów.

Zweryfikowano niezmieniony hash aplikacji i hashe wszystkich modułów końcowej regresji. Szczegóły, liczniki, moduły i pokrycie tras: [OCENY_SPRZEDAWCOW_WYNIKI_2026-11-16.json](OCENY_SPRZEDAWCOW_WYNIKI_2026-11-16.json).

## Ograniczenia i wdrożenie

Nie pozostały niezaliczone testy funkcjonalne w wykonanych zestawach. Dwa pominięte przypadki dotyczą wariantów nie-POSIX w testach kopii kluczy; środowisko jest Linux/POSIX. Telefon sprawdzono jako responsywny Chromium, bez fizycznego iOS/Safari. Funkcja obejmuje jednokrotne gwiazdki za odebrane zamówienie; nie obejmuje komentarzy, edycji ani panelu moderacji.

Migracje `003_seller_ratings.up.sql` i `.down.sql` są ręczne i odwracalne. Testy wykonują upgrade/down/up, odrzucają nieznane polityki i porównują niezmienione zamówienia oraz rekordy finansowe. Pełny rollback usuwa oceny, więc wymaga archiwizacji. Preferowany rollback przywraca kod i zachowuje tabelę do przeglądu.

[Instrukcja obsługi, wdrożenia i rollbacku](OCENY_SPRZEDAWCOW_2026-11-16.md). Nie wykonano wdrożenia. Wcześniejsze ograniczenia produkcyjne #62/#63 pozostają, a przed przyszłym rolloutem trzeba zweryfikować ACL, właścicieli, klucz gateway, odtworzenie kopii i wydajność na kopii docelowego środowiska. Wyniki lokalne nie są deklaracją gotowości produkcyjnej.
