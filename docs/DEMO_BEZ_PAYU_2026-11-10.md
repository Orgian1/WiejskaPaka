# WiejskaPaka — lokalne demo bez PayU

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
Odzyskiwanie hasła używa jednorazowej lokalnej skrzynki, której ścieżkę pokazuje
terminal. Potwierdzanie e-maila i wysyłka potwierdzeń zakupów są testowane
oddzielnie z syntetycznym transportem; ten profil nie uruchamia ich wysyłki.

## Scenariusz końcowej kontroli

1. Gość: sprawdź rejestrację i linki nagłówka, produkty, wyszukiwanie oraz punkt.
2. Klient: zaloguj się, przejrzyj dwie przesyłki, odzyskaj PIN przez hasło,
   sprawdź koszyk i zakup. Dla nowej dostawy wybierz termin i poczekaj na decyzję
   sprzedawcy przed płatnością testową. Jedna paczka ma jedną opłatę dostawy.
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
7. Wyloguj każdą rolę, sprawdź usunięcie prywatnych danych z widoku. Powtórz
   na telefonicznym rozmiarze okna i po obróceniu; bez poziomego przewijania.

## Zasady portfela i granice demo

Kwota wpisana do wypłaty oznacza całą kwotę rezerwowaną z salda. Prowizja
jest w niej zawarta, a nie doliczana drugi raz. Sprzedawca: 500 punktów bazowych
(5%); klient: 0. Zaokrąglenie half-up do grosza przez istniejącą wspólną funkcję.
API nie pozwala klientowi przysłać własnej prowizji. Ponowienie tego samego
wniosku nie powiela rezerwacji. Kontrola obejmuje również starsze zapisy
salda w historii, a nie tylko sumę końcową.

`withdrawal_preview` jest wyceną według stałej polityki tej wersji, obliczaną
również dla wcześniej oczekujących wniosków na podstawie roli konta. Nie jest
niezmiennym, zaksięgowanym potrąceniem. Nie zmieniono schematu ani starych kwot.
Przed zmianą taryfy lub płatnościami rzeczywistymi trzeba zapisywać uzgodnione
warunki operacji w niezmiennej księdze i rozliczać je zdarzeniami operatora.

Portfel pozostaje osobnym podglądem: nie opłaca zakupów, nie otrzymuje przychodów
z zamówień i nie księguje zwrotów zamówień. Te scenariusze działają w istniejącej
symulacji płatności zamówień, z oddzielnymi testami prowizji, zwrotów 75/20/5
oraz 100% przy niedostarczeniu. Nie należy dodawać kwot obu podglądów jako jednego
salda ani obciążać dwukrotnie prowizją. To ograniczenie funkcjonalne jest jawne.

Serwer działa tylko na tym samym urządzeniu (127.0.0.1). Fizyczny telefon
wymaga osobno zabezpieczonego podglądu na VPS. Ułamkowy zakup np. 0,5 kg
pozostaje odrębnym, niewłączonym przepływem; bieżący zakup jednostek jest całkowity.
