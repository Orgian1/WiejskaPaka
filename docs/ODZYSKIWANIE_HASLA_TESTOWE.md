# Odzyskiwanie zapomnianego hasła — lokalne demo

Uruchom `python scripts/run_phone_demo.py`. Skrypt tworzy jednorazową bazę,
włącza odzyskiwanie i wypisuje ścieżkę do prywatnej skrzynki testowej.
W sekcji „Nie pamiętasz hasła?” wpisz syntetyczny adres konta. W pliku JSON
skrzynki znajduje się `fragment`; dopisz go do adresu otwartej strony, np.
`http://127.0.0.1:8765/` i fragment z własnej wiadomości. Przeglądarka wypełni
kod i usunie go z paska adresu. Można również wkleić sam kod do formularza.
Po zmianie zaloguj się nowym hasłem. Skrypt usuwa skrzynkę i bazę po zakończeniu.

Skrzynka służy wyłącznie do testów. Nie wysyła prawdziwych e-maili i nie
potwierdza własności adresu. Nie wpisuj rzeczywistych danych. Osoba mająca
lokalny dostęp do skrzynki ma dostęp do linków; nie udostępniaj jej przez HTTP,
Git, CI ani współdzielony katalog. Windows ACL nie są potwierdzone.

## Ochrona protokołu

- Losowy token zawiera 32 bajty entropii, ważny 15 minut. SQLite przechowuje
  wyłącznie jego SHA-256. Kod trafia do prywatnego pliku wiadomości i pamięci
  formularza, nigdy do odpowiedzi API, URL żądania HTTP ani pamięci trwałej
  przeglądarki. Fragment linku jest usuwany z bieżącego wpisu historii.
- Wydanie linku nie zmienia hasła i nie wylogowuje. Odpowiedź jest taka sama
  dla istniejącego i nieznanego adresu. Nieznany adres otrzymuje w testowej
  skrzynce niezwiązany losowy kod, którego nie można użyć do zmiany hasła.
- Limit wydania: 3 na znormalizowany adres i 100 łącznie w 15 minut. Odmowa
  limitu ma tę samą odpowiedź 202. Kluczem limitu adresu jest jego skrót.
  Limit prób potwierdzenia: 100 łącznie w 15 minut, następnie 429.
  Liczniki są zapisane w SQLite, więc restart procesu ich nie zeruje.
- Potwierdzenie atomowo zmienia hasło Argon2, usuwa wszystkie sesje i wszystkie
  linki resetujące danego konta oraz zdejmuje jego blokadę błędnych logowań.
  Token jest związany z wersją skrótu hasła: zwykła zmiana hasła unieważnia
  wcześniejsze linki. Jednoczesne potwierdzenia mają tylko jednego zwycięzcę.
- Błąd zapisu wycofuje cały reset. Nie zmienia się zakupów, kwot, PIN-ów ani
  klucza szyfrowania zakupów. Odpowiedzi i błędy API mają `no-store`.
- Izolowane odtworzenie przez `sqlite_snapshot.py restore` usuwa także linki
  resetujące odziedziczone z kopii. Cofnięte hasła i uprawnienia nadal wymagają
  osobnej procedury przed ponownym udostępnieniem danych.

## Włączenie i zakres

Poza launcherem demo funkcja jest domyślnie wyłączona. Do jawnego lokalnego
włączenia potrzebne są `WP_ENABLE_TEST_PASSWORD_RESET=1` i
`WP_TEST_RESET_OUTBOX` wskazujący prywatny katalog. Na POSIX katalog ma 0700,
pliki 0600, właścicielem musi być bieżący użytkownik; dowiązanie katalogu jest
odrzucane. Launchery i runner regresji odrzucają odziedziczoną konfigurację
skrzynki, aby nie pisać do wskazanego przez środowisko katalogu użytkownika.

Trasy: GET `/auth/password-reset-test/options`, POST
`/auth/password-reset-test/request` i POST `/auth/password-reset-test/confirm`.
Nie wymagają sesji; potwierdzenie wymaga ważnego kodu. Audyt autoryzacji oznacza
wyłącznie te dokładne pary metoda/ścieżka jako `RECOVERY_TOKEN_FLOW`, nadal
wymagające przeglądu. Nie zwalnia innych endpointów z autoryzacji.

Funkcja pozostaje wyłączona dla PostgreSQL. Dodano wyłącznie schemat do
manifestu nowych jednorazowych baz testowych; nie wykonano produkcyjnej migracji
ani nie podłączono zewnętrznego kanału dostarczania. Globalne limity demo nie zastępują
produkcyjnej ochrony przed nadużyciami, kolejkowania, monitoringu i polityki
retencji wiadomości. Nie deklarujemy odporności na wszystkie kanały czasowe.
Produkcja nadal jest zablokowana. Przyszła integracja musi weryfikować kanał
odbiorcy i zachować jednorazowość, ważność, limity oraz cofnięcie sesji.
