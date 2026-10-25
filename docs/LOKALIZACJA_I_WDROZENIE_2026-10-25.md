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

## Potwierdzenie wdrożenia poprawki

- Operator pobrał commit `9e8e4c2b4a14bc794bd4fa473bf7514031f12896` do `/opt/wiejskapaka/releases/9e8e4c2b`.
- Preflight jako wiejskapaka z preview.env i mail-test.env: success, core i cztery opcjonalne funkcje pocztowe sprawdzone.
- Drop-in `92-location.conf` nadpisuje tylko WorkingDirectory. Venv pozostaje `/opt/wiejskapaka/venv-8ff9bafd`; zależności bez zmian.
- Operator otrzymał LOKALIZACJA_WDROZONA i potwierdził formularz po odświeżeniu strony. Nie wymagano zmiany jednostek poczty.
- Pełne CI commit 9e8e4c2b, run 40195884453: windows_recovery, pełny Windows, PostgreSQL 16/17 i Chromium zakończone SUCCESS. Wrapper fetch_commit_workflow_runs filtruje PR i zwraca pustą listę; workflow jest wyzwalany przez push. Sprawdzać kolekcję actions/runs?head_sha=... przez github.fetch.
- Kolejny krok: odczyt stanu modułu jednostek sprzedaży na VPS, następnie jego migracja/aktywacja, jeżeli nadal wyłączony. Inne wcześniejsze moduły (zdjęcia, wyszukiwanie sprzedawcy, dostawa na adres) też wymagają sprawdzenia flag/tabel.

## Jednostki i poprawka paneli konta

Operator wykonał optional_product_sale_units.sql na wp_test_preview w jednej transakcji i nadał wp_preview_app wyłącznie SELECT,INSERT do obu tabel. Preflight z WP_ENABLE_PRODUCT_UNITS=1 zakończony success. Drop-in 93-product-units.conf aktywny; /product-units zwraca enabled=true, fractional_quantities=false. Dodanie produktu w kg przez sprzedawcę nie zostało jeszcze potwierdzone: operator zgłosił niejasny wybór ról i duży panel konta.

Poprawka paneli: publiczna rejestracja wyłącznie Klient/Sprzedawca; rola w API nadal klient/rolnik dla zgodności danych. Wybór typu przy rejestracji nie przełącza istniejącego konta przy logowaniu. Dodano widoczną nazwę panelu i skrót sprzedawcy, ukrywanie skrótu koszyka poza klientem. Ustawienia bezpieczeństwa zwinięte w details, produkty przed dodatkowymi panelami. Nie przekształcono istniejących kont dostawców/adminów ani nie usunięto ich danych/API. Zgłoszenie koszyka wymaga sprawdzenia na dwóch odrębnych kontach; lokalne testy czyszczenia widoków przechodzą.

Walidacja tej poprawki: 28 testów prywatności, logowania i wyszukiwania przechodzi; dodano rzeczywisty test Chromium klient -> wylogowanie -> sprzedawca na telefonie i desktopie oraz dostosowano otwarcie zwiniętych ustawień w teście weryfikacji e-maila. Testy przeglądarkowe zebrane lokalnie, wykonanie czeka na CI.
