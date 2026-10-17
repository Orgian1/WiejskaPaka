# Odzyskanie PIN-u istniejącego zakupu testowego

W historii zamówień i panelu klienta można wybrać **Odzyskaj PIN istniejącego
zakupu (TEST)**. Trzeba ponownie podać hasło konta. W panelu przesyłki ta sama
operacja odzyskuje wspólny PIN wszystkich jej pozycji. Nie trzeba pamiętać
klucza idempotencji, pierwotnego żądania ani adresu podanego przy zakupie.
Po utracie odpowiedzi lub odświeżeniu strony najpierw zaloguj się i sprawdź
historię; odzyskanie nie uruchamia ponownego zakupu.

## Dostęp i czas

- `POST /orders/{id}/recover-pin-test` oraz
  `POST /shipments/{id}/recover-pin-test`, JSON `{"password":"HASŁO_KONTA"}`.
  Hasło przesyłamy wyłącznie w treści żądania; nie w URL ani logu dostępu.
- Wymagane są aktualna sesja klienta, własność zakupu i poprawne hasło.
  Sesja oraz rola są ponownie weryfikowane w transakcji odczytu sekretu.
  Inny klient dostaje 404, a rolnik, dostawca i administrator 403.
- Limit **5 prób w 15 minut na całe konto**, obejmujący sukcesy i błędy hasła.
  Nowy token, inny zakup, inny endpoint i restart nie zerują limitu.
  Przekroczenie daje 429 z `Retry-After`; nie ogranicza samego logowania.
  Błędy hasła są zapisywane przed odpowiedzią 401, bez wycofywania licznika.
- Odczyt wyłącznie do pierwotnego terminu 24 godzin. Nie przedłużamy retencji.
  PIN wykorzystany, zablokowany, anulowany, refundowany lub należący do
  wygasłej nieopłaconej rezerwacji nie jest ujawniany. Opłacona symulacja
  może być odczytana po terminie rezerwacji, nadal przed limitem retencji.
- Podanie hasła nie generuje ani nie resetuje PIN-u. Nie zeruje pięciu prób
  odbioru, nie przedłuża rezerwacji i nie zmienia zamówień, stocku, płatności,
  dostawy ani pierwotnych warunków. Blokada choćby jednej pozycji przesyłki
  blokuje odzyskanie wspólnego kodu całej przesyłki.
- Odpowiedzi mają `Cache-Control: no-store`. PIN jest wyświetlany przez
  30 sekund; zamknięcie formularza, ukrycie karty, zmiana konta i wylogowanie
  czyszczą widok. Spóźniona odpowiedź nie przywraca wyczyszczonego kodu.
  Hasło jest usuwane z pola przed rozpoczęciem żądania. Nie zapisujemy go,
  tokenu, PIN-u ani adresu w localStorage/sessionStorage.

PIN potwierdza odbiór po sprawdzeniu towaru. Nie ogranicza reklamacji ani
innych ustawowych praw konsumenta. Dostawa na adres nadal jest płatna raz za
przesyłkę, a wina dostawcy nadal oznacza pełny zwrot symulowanej wpłaty.

## Migracja lokalna i PostgreSQL

Nowa tabela `checkout_pin_links` wiąże ID zamówienia z kluczem istniejącego
szyfrogramu; nie zawiera PIN-u. `checkout_pin_access` zawiera tylko ID konta,
liczbę prób i początek okna. Zapis powiązania odbywa się w transakcji zakupu.
Awaria zapisu wycofuje cały zakup, cache, magazyn, koszyk i zapis warunków.

SQLite tworzy tabele automatycznie. Przy starcie aplikacja sprawdza istniejące
szyfrogramy i odtwarza powiązania z uwierzytelnionych ID zamówień, sprawdzając
kupującego. Nie rekonstruuje PIN-u ze skrótu. Migracja nie zmienia terminu ani
szyfrogramu aktywnej odpowiedzi. Sprzeczne dane blokują start zamiast przypisać
cudzy zakup. Podczas odzyskania ponownie porównujemy pełny zestaw zamówień,
ID przesyłki i skróty PIN-u z odszyfrowaną odpowiedzią.

PostgreSQL wymaga ręcznej migracji `database/upgrade_z_checkout_pin_recovery.sql`
**po** istniejących migracjach checkoutu i przesyłek; porządek alfabetyczny
`upgrade_*.sql` spełnia tę zależność. Brak nowych tabel blokuje start nawet przy
pustym cache. Używane są blokady kupującego oraz kolejność: przesyłka, zamówienia.
Migracja poszerza limit klucza w istniejącej tabeli do 107 znaków: publiczne
100 znaków plus siedmioznakowy prefiks `direct:`. Naprawia to rozbieżność
między walidacją HTTP a wcześniejszym ograniczeniem PostgreSQL.

Przed aktualizacją własnej instalacji zatrzymaj starą instancję i zachowaj
spójną kopię bazy oraz osobny klucz. Nie uruchamiamy migracji na Neon ani na
żadnej bazie produkcyjnej. Rzeczywiste wykonanie PostgreSQL wymaga lokalnego
odizolowanego klastra i osobnej bramy testowej; sam zapis SQL nie jest wynikiem PASS.

## Ograniczenia

Odzyskiwanie dotyczy zakupów z zapisanym kluczem idempotencji; interfejs zawsze
wysyła taki klucz. Starszych zakupów bez cache i PIN-ów usuniętych po retencji
nie odtwarzamy. Po 24 godzinach nie należy tworzyć drugiego zakupu tylko po to,
by dostać kod. Bezpieczna obsługa utraty kodu po tym terminie i produkcyjny
kanał dostarczenia PIN-u pozostają do zaprojektowania i niezależnego audytu.
To nadal lokalna aplikacja demonstracyjna, bez rzeczywistych płatności.
