# WiejskaPaka — uruchomienie i odbiór przez właściciela

Gałąź: `codex/product-categories-filters-20261113` w `Orgian1/WiejskaPaka`.
To lokalne demo z fikcyjnymi kontami i symulowanymi płatnościami. Nie wymaga VPS.

## Uruchomienie na komputerze

Pobierz wskazaną gałąź do **nowego** katalogu (jeżeli nazwa jest zajęta, wybierz
inną; nie nadpisuj istniejących plików):

```bash
git clone --branch codex/product-categories-filters-20261113 --single-branch https://github.com/Orgian1/WiejskaPaka.git WiejskaPaka-odbior
cd WiejskaPaka-odbior
git rev-parse HEAD
```

Porównaj SHA z końcowym raportem. W katalogu projektu, z Pythonem 3.12:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/run_phone_demo.py --full-demo --public-geocoder photon
```

Na Windows zamiast `.venv/bin/python` użyj `.venv\Scripts\python.exe`.
Nie przestawiaj istniejącego checkoutu z lokalnymi zmianami. W pobranym wydaniu
potwierdź `git branch --show-current` i `git rev-parse HEAD`; nie używaj `main`.

Skrypt pokazuje lokalny adres do otwarcia **na tym komputerze** i cztery losowe
konta: klienta, sprzedawcy (`rolnik`), dostawcy i administratora. Korzystaj z kont
z bieżącego uruchomienia. Nie udostępniaj terminala z hasłami ani zrzutów tych danych.
Na POSIX można użyć `--credentials-file /prywatny/katalog/konta.json`; katalog musi
należeć do użytkownika i mieć uprawnienia 0700, a plik nie może wcześniej istnieć.
Po zakończeniu podglądu plik zostanie usunięty. Ctrl+C kończy demo.

Każde nowe uruchomienie tworzy nową bazę i nowe konta; zamknięcie usuwa dane demo.
Kolejność punktów, ulubione i zapisane lokalizacje pozostają na kontach tak długo,
jak działa ta instancja demo. Na trwałej bazie są zachowywane także po restarcie.

## Photon, mapa i lokalizacja

Podana komenda jawnie włącza Photon: `https://photon.komoot.io/api/`, język polski,
wyniki z Polski. Możesz podać samą miejscowość albo miejscowość i ulicę z numerem budynku
w polu ulicy, np. „Marszałkowska 1”. Następnie kliknij wyszukiwanie.
Dostępność numeru zależy od danych OpenStreetMap/Photon; brak trafienia nie
potwierdza, że adres nie istnieje.
Zapytanie adresowe jest przekazywane publicznej usłudze dopiero po kliknięciu;
nie wpisuj prywatnych danych klientów. Wynik jest orientacyjny — sprawdź znacznik.
Publiczne demo ma limit 1 zapytania/s i 120/h, przy jednym procesie serwera.
Przy większym użyciu potrzebna jest własna/zakontraktowana usługa Photon.

W środowisku chmurowym podczas odbioru technicznego proxy blokuje dostęp do
Photon (`403` przy zestawianiu połączenia). Aplikacja zwraca wówczas kontrolowany
komunikat niedostępności (`503`), bez ujawniania treści zapytania. Nie oznacza to
potwierdzenia dostępności publicznej usługi na komputerze właściciela.

Można nadal wybrać punkt na lokalnej mapie poglądowej albo użyć GPS po wyrażeniu
zgody. Mapa poglądowa nie pokazuje ulic. Szczegółowe kafelki OpenStreetMap są
opcjonalne i wymagają osobnego dostępu do `tile.openstreetmap.org`.
Bez `--public-geocoder photon` wyszukiwanie ogranicza się do zapisanych punktów.

Kategorie i łączone filtry: [dodatkowa lista odbioru](KATEGORIE_I_FILTRY_2026-11-13.md).

## Lista odbioru

Przed zmianą roli wyloguj się. Pole typu konta dotyczy rejestracji; podczas
logowania decyduje konto, którego e-mail i hasło podajesz.

| Rola | Co sprawdzić | Oczekiwany wynik |
| --- | --- | --- |
| Klient | Rozwiń produkt, kliknij serce, przejdź do Ulubionych, wyloguj i zaloguj ponownie | Szczegóły pod odpowiednim rzędem; ulubiony produkt nadal zapisany |
| Klient | Blisko mnie: GPS za zgodą i zapis lokalizacji | Oferty według wybranej/zapisanej lokalizacji; odmowa GPS nie blokuje ręcznego wyboru |
| Sprzedawca | Aktualne zamówienia i Uzupełnij towar | Te dwa panele rozwinięte; pozostałe zwinięte po nowym logowaniu |
| Sprzedawca | Rozwiń punkt w aktualnych zamówieniach | Liczba zamówień, numery, produkty, ilości i statusy |
| Sprzedawca | Dodaj drugi punkt, zmień kolejność w górnym menu, otwórz Nawigację | Mapy Google otrzymują punkty we wskazanej kolejności; dłuższa trasa ma kolejne części |
| Sprzedawca | Zaloguj to samo konto w drugiej przeglądarce w tej samej instancji demo | Taka sama kolejność punktów; „Odśwież kolejność z konta” pobiera najnowszą wersję |
| Sprzedawca | Zmień kolejność w obu otwartych przeglądarkach bez odświeżania drugiej | Drugi zapis ze starą wersją zostaje odrzucony; lista pobiera aktualną kolejność |
| Klient i sprzedawca | Nowe zamówienie z dostawą na adres, alternatywny termin sprzedawcy, decyzja klienta | Płatność testowa dostępna po zgodzie; rezerwacja nie jest przedłużana propozycją |
| Klient i sprzedawca | Odbiór gotowej przykładowej przesyłki | Klient sprawdza towar i podaje PIN; sprzedawca potwierdza całą przesyłkę, bez dodatkowego checkboxa |
| Dostawca | „Pokaż trasę aktywnych dostaw”, sprawdzenie trasy i przejście do Map Google | Tylko aktywne przydzielone adresy, bez duplikowania miejsca dla produktów jednej przesyłki |
| Dostawca | Przypisana przykładowa przesyłka, potwierdzenie PIN-em | Jednorazowy odbiór; po zakończeniu znika dostęp do adresu dostawy |
| Administrator | Kolejka sprzedawców, testowa decyzja z uzasadnieniem, raport i CSV | Własny panel administratora, zapis decyzji, pobieranie raportu testowego |
| Administrator i sprzedawca | Kod promocyjny na trzy punkty | Kod konfigurowany przez administratora; sprzedawca nie może wykorzystać go drugi raz |
| Wszystkie role | Wylogowanie | Prywatne dane poprzedniego konta znikają z widoku |

PIN odzyskaj jako klient, w panelu przesyłki, podając hasło klienta z bieżącego
demo. Użyj go jako sprzedawca dla odbioru albo jako dostawca dla dostawy.
Powtórne potwierdzenie nie może ponownie zakończyć ani rozliczyć przesyłki.
Numery telefonów nie powinny pojawiać się w panelach stron transakcji.

## Komputer i telefon

Najpierw sprawdź pełne okno komputera oraz tryb urządzenia w narzędziach
przeglądarki: szerokości 320, 360, 390, 768 i 1280 px. Formularze, menu punktów,
serca i rozwijane zamówienia nie powinny wymagać przewijania poziomego.
Emulacja dotyku nie zastępuje odbioru na fizycznym telefonie.

### Ten sam podgląd na prawdziwym telefonie przez Wi-Fi

Domyślny launcher jest lokalny. Opcjonalny `--host` pozwala wskazać konkretny
prywatny adres IPv4 komputera (10.x, 172.16–31.x albo 192.168.x) i wymaga HTTPS.
Nie akceptuje `0.0.0.0` ani adresów publicznych. Komputer i telefon muszą być
w tej samej zaufanej sieci Wi-Fi, bez izolacji urządzeń. Nie przekierowuj portu
w routerze. W zaporze dopuszczaj tylko telefon/swoją sieć do portu demo.

1. Ustal adres IPv4 komputera w ustawieniach sieci. Poniższe `192.168.1.20`
   jest przykładem — zastąp go swoim adresem we wszystkich poleceniach.
2. Przygotuj zaufany lokalny certyfikat obejmujący ten IP. Możesz użyć bezpłatnego
   [mkcert](https://github.com/FiloSottile/mkcert#installation), instalowanego
   zgodnie z oficjalną instrukcją. Nie wymaga usługi zewnętrznej ani klucza API.
   Własny katalog certyfikatów przechowuj **poza repozytorium**. Przykład POSIX:

   ```bash
   mkdir -m 700 /tmp/wiejskapaka-owner-tls
   mkcert -install
   mkcert -cert-file /tmp/wiejskapaka-owner-tls/demo.pem -key-file /tmp/wiejskapaka-owner-tls/demo-key.pem 192.168.1.20 localhost 127.0.0.1 ::1
   ```

   Jeśli katalog już istnieje, wybierz nowy prywatny katalog. Na Windows wybierz
   własny prywatny katalog i odpowiednio zamień ścieżki.
3. Na telefon przenieś wyłącznie publiczny certyfikat `rootCA.pem` z katalogu
   pokazanego przez `mkcert -CAROOT`. **Nigdy nie kopiuj `rootCA-key.pem` ani
   `demo-key.pem` na telefon, do GitHuba ani do zgłoszeń.** Zainstaluj ten CA
   jako zaufany certyfikat użytkownika. Na iOS po instalacji profilu włącz pełne
   zaufanie w ustawieniach zaufania certyfikatów; na Androidzie użyj instalacji
   certyfikatu CA w ustawieniach zabezpieczeń. Nazwy ekranów zależą od systemu.
4. Zakończ wcześniejsze demo przez Ctrl+C i uruchom jedną nową instancję:

   ```bash
   .venv/bin/python scripts/run_phone_demo.py --full-demo --public-geocoder photon --host 192.168.1.20 --ssl-certfile /tmp/wiejskapaka-owner-tls/demo.pem --ssl-keyfile /tmp/wiejskapaka-owner-tls/demo-key.pem
   ```

5. Na komputerze i telefonie wpisz adres HTTPS z terminala, z tym samym IP
   i portem. Zaloguj ten sam e-mail sprzedawcy z **nowego** uruchomienia demo.
   Nie kontynuuj przez ostrzeżenie o niezaufanym certyfikacie — popraw zaufanie
   CA/adres certyfikatu; GPS wymaga bezpiecznego kontekstu. Zezwól na lokalizację
   dopiero po kliknięciu GPS. Nie musisz otwierać portu do internetu.
6. Zmień kolejność punktów na komputerze, na telefonie kliknij „Odśwież kolejność
   z konta”. Porównaj listę i części nawigacji. Następnie wykonaj listę odbioru
   dla pozostałych ról. Błąd otwarcia strony przy poprawnym certyfikacie oznacza
   zwykle zaporę, izolację Wi-Fi albo nieprawidłowy IP.
7. Po odbiorze Ctrl+C zamyka demo i usuwa jego bazę. Usuń tymczasowe certyfikaty
   demo oraz niepotrzebny profil CA z telefonu. Nie usuwaj innych zaufanych CA.

Zweryfikowano uruchomienie launchera przez HTTPS z rzeczywistą weryfikacją
certyfikatu na loopback. Samo połączenie z fizycznym telefonem i instalacja CA
pozostają czynnością właściciela — środowisko testowe nie ma jego urządzenia.

Zapisz wynik jako: rola → czynność → wynik oczekiwany → wynik faktyczny →
rozmiar ekranu/przeglądarka. Do zgłoszeń dołączaj zrzuty bez haseł, PIN-ów,
adresów i danych osobowych. Szczegóły bezpiecznej aktualizacji są w
[procedurze VPS](AKTUALIZACJA_VPS_ODBIOR_2026-11-13.md).
