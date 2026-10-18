# Profil rolnika i zasady wersji testowej — 18.10.2026

Dodano panel sprawdzania stanu profilu i potwierdzania zasad demo.
Potwierdzenie wymaga jawnego zaznaczenia zapoznania się z widocznym tekstem;
powtórzone żądanie jest idempotentne. Dane są czyszczone przy zmianie konta.
Odpowiedzi rozpoczęte w poprzedniej sesji nie mogą wypełnić nowego panelu.

Przypomnienie od 20 zakończonych transakcji jest regułą produktu. Przesyłka
wieloproduktowa liczy się raz po odebraniu wszystkich pozycji. Dawne odebrane
zamówienia bez przesyłki są liczone osobno. Częściowe odbiory, anulowania,
nieudane dostawy i cudze zamówienia nie zwiększają licznika. Potwierdzenie
zasad pozostawia profil w oczekiwaniu na testowy przegląd; nie włącza wypłat.

Nie dodano zbierania tożsamości ani danych bankowych. Nie ma blokady sprzedaży
po przekroczeniu progu. Szczegóły: `PROFIL_ROLNIKA_TESTOWY.md`.

Testy celowane: **63 zaliczone, 0 błędów, 2 pominięte** (lokalnie brak
Chromium). Wynik: `audits/seller_profile_targeted_2026-10-18.json`.
Obejmują granice progu, powiązania pozycji, role i zgodę HTTP, idempotencję,
zmianę konta w trakcie żądania, błąd sieci i podwójne kliknięcia. Wspólny
scenariusz HTTP sprawdza, że odbiór dwóch produktów w jednej przesyłce daje
jedną zakończoną transakcję. Jest także w natywnym zestawie PostgreSQL.

Kod funkcji: `13865f9183100b5355bf7f550094248cb0815ac8`.
Test Chromium uzupełniono o jawne oczekiwanie na odpowiedź odczytu API
w commicie `6ef815dec3b4043c64ec1977ce892b453b61d57c`.
Pierwszy przebieg miał dwa timeouty nowego scenariusza; aktualny zaliczył go
na obu szerokościach. Nie utożsamiamy tej zmiany testu z naprawą błędu API.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39100557092
Bramki wymagają 16 testów PostgreSQL, 11 przeglądarkowych oraz wstępnych
39 testów odzyskiwania Windows bez błędów i pominięć. Następnie Windows
wykonuje pełną regresję. Zestaw wstępny jest powtarzanym podzbiorem pełnego.
Wyniki oczekujące nie stanowią zaliczenia; wcześniejsze przebiegi dotyczą
wcześniejszych commitów. Gałąź `main` pozostaje bez zmian.

Natywne dowody dla bieżącego commitu: PostgreSQL **16/16**, Chromium **11/11**
i kontrola HTTP przy pięciu szerokościach okna. Obie bramy bez SKIP; odciski
kodu, testów i zależności porównano z lokalnym repozytorium. Zweryfikowane
artefakty: `audits/seller_profile_ci_2026-10-18/`. Windows w chwili zapisu
raportu nadal wykonuje pełną regresję; nie przypisujemy mu wyniku PASS.

Końcowa pełna regresja Linux: **3676 zaliczonych, 0 błędów, 22 pominięte**
(3698 przypadków, 294/294 moduły). Źródła pozostały niezmienione podczas
wykonania. Dowód: `audits/seller_profile_linux_2026-10-18.json`. Pominięcia
obejmują testy wymagające natywnych usług lub przeglądarki; ich osobne
wyniki CI powyżej nie są dodawane do liczby odrębnych przypadków.
