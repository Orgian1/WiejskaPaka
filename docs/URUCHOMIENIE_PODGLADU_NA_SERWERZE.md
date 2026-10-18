# Pakiet uruchomienia zamkniętego podglądu

Stan: 18.10.2026. Szablony przygotowano do instalacji przez administratora;
nie zainstalowano usługi na serwerze. Docelowo Ubuntu 24.04, Python 3.12,
PostgreSQL 16. Pierwsze uruchomienie służy testom na sztucznych danych.
Rolnik i sprzedawca oznaczają to samo konto i tę samą rolę.

## Układ instalacji

| Ścieżka | Zawartość i dostęp |
| --- | --- |
| /opt/wiejskapaka/app | Sprawdzona wersja repozytorium; właściciel root, aplikacja tylko czyta |
| /opt/wiejskapaka/venv | Środowisko Python z requirements-lock.txt; aplikacja tylko czyta |
| /etc/wiejskapaka/preview.env | Konfiguracja poza repozytorium, root:root, 0600 |
| /var/lib/wiejskapaka | Stan usługi, użytkownik wiejskapaka, 0700 |
| /var/lib/wiejskapaka/checkout-key.json | Stały klucz sejfu, wiejskapaka, 0600; bez dowiązań |

Konto systemowe `wiejskapaka` nie otrzymuje sudo ani dostępu do logowania.
Serwer PostgreSQL nasłuchuje lokalnie. Aplikacja używa osobnej roli
bez SUPERUSER, CREATEDB, CREATEROLE i BYPASSRLS oraz bez prawa tworzenia tabel.
Konto administrujące bazą nie trafia do konfiguracji aplikacji.

## Kolejność przygotowania

1. Po zakupie serwera skonfigurować aktualizacje, dostęp SSH kluczem i zaporę.
   Nie otwierać portów 8000 ani 5432 na Internet. Zachować awaryjny dostęp
   administratora przed zmianą zasad SSH.
2. Umieścić uzgodniony commit w katalogu aplikacji, utworzyć środowisko Python
   i zainstalować zależności z `requirements-lock.txt`.
3. Utworzyć nową pustą bazę `wp_test_preview`. Zweryfikować pakiet SQL:
   `python -m database.verify_test_migrations`. Administrator przegląda
   kolejność BASE i UPGRADES w `database/test_schema_manifest.py`, wykonuje
   wskazane pliki z zatrzymaniem na błędzie i nadaje ograniczonej roli prawa
   do wymaganych tabel i sekwencji. Nie uruchamiać tego na istniejącej bazie.
   Samo sprawdzenie manifestu nie wykonuje migracji.
4. Utworzyć katalog stanu i klucz przez `scripts/checkout_keys.py create --path`
   ze wskazaniem powyższej bezwzględnej ścieżki. Klucz tworzy się raz;
   kolejne restarty korzystają z niego ponownie. Zachować chronioną kopię.
5. Skopiować `deploy/preview/preview.env.example` do pliku konfiguracji poza
   repozytorium. Ustawić prywatnie nowe hasło roli; znaki specjalne w URL
   wymagają kodowania procentowego. Usunąć wartość REPLACE_ME.
6. Skopiować jednostkę do `/etc/systemd/system/wiejskapaka-preview.service`.
   Wykonać `systemd-analyze verify` dla jednostki, następnie `systemctl
   daemon-reload` i `systemctl start wiejskapaka-preview`. Na tym etapie nie
   włączać automatycznego startu przed odbiorem. ExecStartPre sprawdzi
   konfigurację, klucz, połączenie, rolę i rdzeń schematu bez zapisu do bazy.
7. Połączyć się z własnego komputera przez
   `ssh -N -L 18000:127.0.0.1:8000 UZYTKOWNIK@SERWER` i otworzyć
   `http://127.0.0.1:18000`. Wykonać odbiór opisany poniżej.

Jednostka nie wykonuje migracji, nie tworzy kont demonstracyjnych i nie
generuje nowego klucza przy starcie. Nie uruchamiać obok niej efemerycznego
launchera demonstracyjnego, jeżeli celem jest zachowanie danych po restarcie.

## Odbiór na zakupionym serwerze

- Rejestracja i logowanie kupującego oraz rolnika/sprzedawcy; katalog,
  koszyk i dostęp do właściwego panelu.
- Odrzucenie dostępu innego konta do zamówień i adresów.
- Restart jednostki: zachowanie kont, katalogu i istniejących danych;
  brak ponownego tworzenia klucza i brak automatycznych migracji.
- Potwierdzenie lokalnego nasłuchu i braku dostępu do API/bazy z Internetu.
- Sprawdzenie logów pod kątem błędów; logów nie publikować bez przeglądu.

Płatności rzeczywiste i symulowane są w szablonie wyłączone. Scenariusze
zakupów wymagające symulatora uruchamiać oddzielnie na sztucznych danych
po świadomym ustawieniu WP_ENABLE_TEST_PAYMENTS=1. Nie dodawać kluczy PSP.

## Kopia i odtworzenie — warunek przed danymi użytkowników

Testy restartu procesu na PostgreSQL zostały zaliczone; nie są testem
odtworzenia serwera z kopii. Istniejące szyfrowane narzędzie snapshotów
SQLite nie obsługuje PostgreSQL i nie wolno go tu traktować jako backupu.
Przed rzeczywistymi danymi trzeba przygotować szyfrowaną kopię PostgreSQL
wraz z odpowiadającym jej kluczem sejfu, przechowywać ją poza serwerem,
a następnie odtworzyć w oddzielnej bazie i sprawdzić odczyt zamówień.
Bez tego punktu podgląd pozostaje środowiskiem sztucznych danych.

## Poczta i publikacja

Jutro potrzebne będą domena, skrzynka obsługi i parametry dostawcy wysyłki
wiadomości aplikacyjnych: host, port, TLS oraz możliwość ustawienia
SPF/DKIM/DMARC. Sama skrzynka nie potwierdza działania wiadomości z aplikacji.
Hasła wprowadza administrator poza repozytorium i czatem. Podłączenie,
test dostarczenia i obsługa błędów wysyłki stanowią osobny etap.

Publiczna domena, HTTPS i dopuszczenie prawdziwych użytkowników wymagają
osobnego odbioru. Ten pakiet przygotowuje prywatny podgląd; nie usuwa
blokady trybu produkcyjnego i nie potwierdza wydajności dla planowanego ruchu.

## Weryfikacja przygotowania

Lokalnie: 20 testów kontroli podglądu, schematu i launchera SSH zaliczonych;
manifest SQL zweryfikowany; konfiguracja przykładowa przechodzi walidację
launchera. Dyrektywy jednostki sprawdzono przez systemd-analyze verify
na tymczasowej kopii z zastępczym programem, ponieważ docelowa ścieżka
interpretera jeszcze nie istnieje. Nie jest to test startu jednostki na VPS.
Po instalacji trzeba powtórzyć weryfikację z rzeczywistym interpreterem.
