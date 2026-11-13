# WiejskaPaka — uruchomienie i odbiór przez właściciela

Gałąź: `codex/demo-finalization-fixes-20261112` w `Orgian1/WiejskaPaka`.
To lokalne demo z fikcyjnymi kontami i symulowanymi płatnościami. Nie wymaga VPS.

## Uruchomienie na komputerze

W katalogu pobranego projektu, z Pythonem 3.12:

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
wyniki z Polski. Wpisz miejscowość i ulicę, a następnie kliknij wyszukiwanie.
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

Launcher celowo nasłuchuje tylko na pętli lokalnej. Samo wpisanie lokalnego
adresu komputera w telefonie nie połączy z tym demo. Odbiór fizycznym telefonem
wymaga osobnego, uwierzytelnionego połączenia z HTTPS przygotowanego przez
operatora, bez zmiany istniejącego podglądu i bez publicznego wystawiania portu
z płatnościami testowymi. Lokalizacja urządzenia wymaga bezpiecznego kontekstu
przeglądarki i osobnej zgody. Takiego połączenia ani wdrożenia tu nie wykonano.

Zapisz wynik jako: rola → czynność → wynik oczekiwany → wynik faktyczny →
rozmiar ekranu/przeglądarka. Do zgłoszeń dołączaj zrzuty bez haseł, PIN-ów,
adresów i danych osobowych. Szczegóły bezpiecznej aktualizacji są w
[procedurze VPS](AKTUALIZACJA_VPS_ODBIOR_2026-11-13.md).
