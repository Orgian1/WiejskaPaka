# WiejskaPaka — lokalne demo bez PayU

Stan bieżący i komplet wyników: `ODBIOR_KONCOWY_DEMO_2026-11-10.md`.

## Uruchomienie

Z katalogu projektu, Python 3.12, Node (do testów JavaScript):

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/run_phone_demo.py --full-demo
```

Linux/macOS:

```bash
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/run_phone_demo.py --full-demo
```

Otwórz `http://127.0.0.1:8765`. Terminal pokazuje osobne, losowe dane logowania
klienta, sprzedawcy, dostawcy i administratora. Nie ma uniwersalnego hasła.
Serwer rozpoznaje rolę z konta. Lista typu konta dotyczy tylko rejestracji.
Po zamknięciu przez Ctrl+C baza demo jest usuwana; następny start daje nowe dane.
Konta i dane z wcześniejszych sesji nie są otwierane ani zmieniane.

## Zakres profilu

Włączone są jednostki sprzedaży, zdjęcia (istniejące limity: produkt 500 KB,
pozostałe 1 MB), publiczne loginy sprzedawców, kalendarz punktu, terminy dostawy
na adres i prywatny portfel. Fikcyjny sprzedawca ma login `gospodarstwo_demo`.
Punkt ma datę obecności za siedem dni; dostawa ma zaakceptowane okno czasowe.
Dwie przesyłki mają po dwa produkty, a dostawa kosztuje łącznie 5,01 zł.
Profil nie dziedziczy konfiguracji baz, PayU, SMTP, kluczy ani workerów z otoczenia.
Zwykły odbiór, po poprawnej rezerwacji towaru i udanej płatności testowej,
automatycznie staje się gotowy do odbioru. W pełnym demo włączona jest flaga
WP_ENABLE_AUTOMATIC_PICKUP=1. Nie trzeba ręcznego zatwierdzenia sprzedawcy
ani zaznaczania checkboxa kontroli towaru; wydanie nadal wymaga jednorazowego PIN-u.
Odzyskiwanie hasła używa jednorazowej lokalnej skrzynki, której ścieżkę pokazuje
terminal. Potwierdzanie e-maila i wysyłka potwierdzeń zakupów są testowane
oddzielnie z syntetycznym transportem; ten profil nie uruchamia ich wysyłki.

## Scenariusz końcowej kontroli

1. Gość: sprawdź rejestrację i linki nagłówka, produkty, wyszukiwanie oraz punkt.
2. Klient: zaloguj się, przejrzyj dwie przesyłki, odzyskaj PIN przez hasło,
   sprawdź koszyk i zakup. Dla nowej dostawy wybierz termin i poczekaj na decyzję
   sprzedawcy przed płatnością testową. Jedna paczka ma jedną opłatę dostawy.
   Sprzedawca może zamiast akceptacji zaproponować inną datę i zakres godzin;
   klient przyjmuje lub odrzuca tę propozycję w zakładce dostaw.
3. Sprzedawca: sprawdź produkty, jednostki, stan magazynu, zdjęcia, profil,
   login, daty w punkcie i okna dostaw. Zatwierdź nową dostawę w panelu.
4. Odbiór: sprzedawca potwierdza przesyłkę odbiorową PIN-em klienta po sprawdzeniu
   towaru; dostawca potwierdza dostawę. Adres zakończonej dostawy przestaje być
   dostępny dostawcy. PIN portfela i PIN odbioru to dwa osobne mechanizmy.
5. Portfel klienta i sprzedawcy: doładuj 100 zł, ustaw osobny sześciocyfrowy PIN,
   wpisz wypłatę 40 zł. Klient: prowizja 0 zł, po potrąceniu 40 zł.
   Sprzedawca: prowizja 2 zł, po potrąceniu 38 zł. Rezerwacja wynosi 40 zł,
   dostępne saldo 60 zł. Odśwież stronę i sprawdź historię. Nie ma przelewu.
6. Administrator: przegląd profilu sprzedawcy, zgłoszenia, miesięczny raport
   finansowy i CSV. Dokładny scenariusz rozliczeń: `DEMO_Z_DANYMI.md`.
   W zakładce wypłat zakończ testowy wniosek sprzedawcy: rezerwa znika,
   dostępne saldo pozostaje 60 zł, a historia zachowuje 38 zł netto i 2 zł
   prowizji. Osobny nowy wniosek anuluj jako właściciel: cała rezerwa wraca
   do salda bez prowizji. Nie następuje przelew bankowy.
7. Wyloguj każdą rolę, sprawdź usunięcie prywatnych danych z widoku. Powtórz
   na telefonicznym rozmiarze okna i po obróceniu; bez poziomego przewijania.
8. Klient: wybierz miejsce, wyszukaj produkty, dodaj ofertę serduszkiem i otwórz
   „Ulubione”. Po ponownym zalogowaniu na tym samym urządzeniu „Blisko mnie”
   użyje zapamiętanego miejsca. Sprawdź usuwanie ulubionego i czyszczenie lokalizacji.

Lokalizacja i usługa mapowa mają granice opisane w
`ODBIOR_LOKALIZACJA_ULUBIONE_DOSTAWY_2026-11-10.md`. Brak sygnału GPS lub zgody
systemowej nie oznacza znalezienia położenia; aplikacja pokaże właściwy komunikat.

## Zasady portfela i granice demo

Kwota wpisana do wypłaty oznacza całą kwotę rezerwowaną z salda. Prowizja
jest w niej zawarta, a nie doliczana drugi raz. Sprzedawca: 500 punktów bazowych
(5%); klient: 0. Zaokrąglenie half-up do grosza przez istniejącą wspólną funkcję.
API nie pozwala klientowi przysłać własnej prowizji. Ponowienie tego samego
wniosku nie powiela rezerwacji. Kontrola obejmuje również starsze zapisy
salda w historii, a nie tylko sumę końcową.

Wnioski mają niezmienny zapis warunków: rola, kwota brutto, stawka, prowizja
i netto. Zmiana roli nie przelicza zapisanej prowizji. Starsze wnioski otrzymują
warunki podczas migracji według dotychczasowej polityki. Anulowanie i zakończenie
są osobnymi niezmiennymi zdarzeniami; tylko jeden stan końcowy może wygrać.
To nadal symulacja, bez zaksięgowania potrącenia przez operatora.
Opis migracji i obsługi: `WYPLATY_DEMO_ETAP2_2026-11-10.md`.

Przy utracie odpowiedzi operacji użyj przycisku jej sprawdzenia. Serwer zwraca
istniejący wynik albo trwale blokuje stary klucz przed spóźnionym księgowaniem.
Dopiero potem podaj nową kwotę. Nie czyść samodzielnie pamięci karty, aby obchodzić
to sprawdzenie. Szczegóły: `ODZYSKIWANIE_OPERACJI_PORTFELA_2026-11-10.md`.

Portfel pozostaje osobnym podglądem: nie opłaca zakupów, nie otrzymuje przychodów
z zamówień i nie księguje zwrotów zamówień. Te scenariusze działają w istniejącej
symulacji płatności zamówień, z oddzielnymi testami prowizji, zwrotów 75/20/5
oraz 100% przy niedostarczeniu. Nie należy dodawać kwot obu podglądów jako jednego
salda ani obciążać dwukrotnie prowizją. To ograniczenie funkcjonalne jest jawne.

Serwer działa tylko na tym samym urządzeniu (127.0.0.1). Fizyczny telefon
wymaga osobno zabezpieczonego podglądu na VPS. Ułamkowy zakup np. 0,5 kg
pozostaje odrębnym, niewłączonym przepływem; bieżący zakup jednostek jest całkowity.
