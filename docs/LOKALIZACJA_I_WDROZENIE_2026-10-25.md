# Lokalizacja i stan wdrożenia — 25 października 2026

## Potwierdzone przez operatora na VPS

- Nowa wersja 8ff9bafd działa z `/opt/wiejskapaka/releases/8ff9bafd`, z osobnym venv. Stary `/opt/wiejskapaka/app` zachowany.
- `test.wiejskapaka.pl` prowadzi tunelem do 127.0.0.1:8000. Cloudflare Access ma regułę Allow dla jednego adresu operatora; walidacja Access w tunelu włączona. Operator loguje się kontem Cloudflare; OTP nie dodano.
- Migracje poczty wykonane. Weryfikacja e-maila i potwierdzenie zamówienia przetestowane przez operatora z rzeczywistym SES. Numer, produkty, kwota i PIN zgodne. Kolejne potwierdzenie dotarło automatycznie.
- Obie jednostki `wiejskapaka-mail@verification.timer` oraz `wiejskapaka-mail@order_confirmation.timer` sprawdzają kolejki co ok. 30 sekund. W logach IDLE bez błędów. Wspólny limit 10 wiadomości/24h i odstęp 2 s; SES nadal traktować jako sandbox, dopóki nie ma potwierdzenia zmiany limitów.
- Poczta korzysta z osobnego chronionego `/etc/wiejskapaka/mail-test.env` i drop-in `91-mail-test.conf`. Sekrety poza repozytorium. Nie drukować ich zawartości.
- Drop-in `90-release.conf` wskazuje wersję aplikacji. Kontrola po restarcie musi poczekać na HTTP 401 na `/auth/me`; pierwsza próba bez oczekiwania wycofała poprawny start za wcześnie.
- Główna domena i DNS SES pozostają bez zmian. PayU oraz feedback SES nie są uruchomione. Kopia bazy istnieje, pełny test odtworzenia nadal niewykonany.

## Poprawka wyszukiwania lokalizacji

Współrzędne wyszukiwania są ukrytymi wartościami, także bez skonfigurowanego geokodera lub przy błędzie jego konfiguracji. GPS nadal wymaga kliknięcia i zgody przeglądarki.

Bez geokodera formularz wyszukuje maksymalnie 5 aktywnych, zapisanych punktów odbioru z lokalizacją po prefiksie miejscowości i opcjonalnie ulicy. Nie wysyła adresów zewnętrznym usługom. Wybór jest jawny; odległość liczona od wybranego punktu, a nie automatycznie od środka miejscowości lub domu. Nie obejmuje miejsc bez zapisanych punktów z lokalizacją. Kod pocztowy jest wtedy ukryty, bo baza punktów go nie przechowuje; API nie ignoruje go po cichu.

Skonfigurowany geokoder zachowuje dotychczasową obsługę adresów, kodów pocztowych i wielu kandydatów. Pola lokalizacji w edytorze punktu sprzedawcy nie są objęte tą poprawką wyszukiwarki.

Walidacja lokalna: testy adresów/API/JS 24 passed, test pełnego lokalnego marketplace HTTP 1 passed, testy czyszczenia lokalizacji po wylogowaniu 4 passed, node syntax checks i git diff --check poprawne. Chromium lokalnie niedostępne; ta poprawka nie ma jeszcze potwierdzonego pełnego CI ani testu na VPS.

Wdrażać jako nowy worktree i nowe wskazanie `90-release.conf`, bez zmiany istniejących jednostek poczty i ich venv. Nie resetować starego katalogu ani bazy. Po wdrożeniu sprawdzić wyszukiwanie GPS i miasta; wynik pusty jest prawidłowy, gdy brak aktywnych punktów z zapisanymi współrzędnymi.
