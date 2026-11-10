# Zamknięty podgląd na serwerze przez SSH

Pakiet przygotowawczy do testu na VPS bez domeny, płatności i publicznego
portu aplikacji. Nie wdrożono go na zewnętrznym serwerze. Nie potwierdza
wydajności 5000 klientów dziennie ani gotowości produkcyjnej.

## Zakres

Proces aplikacji słucha wyłącznie na 127.0.0.1. Tester otwiera ją przez tunel
SSH. Używamy istniejącego demo SQLite: fikcyjnych czterech ról, dwóch ofert,
odbioru i dostawy z symulacją płatności. Rolnik i sprzedawca to ta sama rola.
Po zakończeniu procesu dane demo są usuwane; to nie trwała instalacja.
PostgreSQL i odtwarzanie jego kopii na VPS są następnym, odrębnym etapem.
Nie usuwać blokady trybu produkcyjnego, nie otwierać portu 8765 w firewallu.

## Przygotowanie — zwykłe konto Linux z dostępem SSH

Na własnym serwerze przygotować Python 3.12, venv i checkout gałęzi
`wiejskapaka-import`. Nie uruchamiać aplikacji jako root. W katalogu projektu:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
```

Prywatny katalog kont musi należeć do użytkownika uruchamiającego podgląd
oraz mieć uprawnienia 0700. Plik ma być nowy, poza repozytorium i katalogiem
serwowanym przez HTTP. Launcher nie nadpisuje istniejących plików lub linków.

```bash
install -d -m 700 "$HOME/wiejskapaka-preview-private"
.venv/bin/python scripts/run_phone_demo.py --sample-data --port 8765 \
  --credentials-file "$HOME/wiejskapaka-preview-private/accounts.json"
```

Powyższy proces pozostawić w terminalu. Port jest stały tylko dla wygody
instrukcji; można wybrać inny wolny port 1024–65535. Launcher nie podłącza
zewnętrznej bazy, klucza ani prawdziwych płatności odziedziczonych z otoczenia.
Nie wypisuje haseł, gdy podano `--credentials-file`. Bez tego parametru
zachowuje dotychczasowy lokalny tryb wypisujący jednorazowe konta.

## Dostęp testera

Na komputerze testera w osobnym terminalu, po zastąpieniu konta i adresu:

```bash
ssh -N -L 127.0.0.1:8765:127.0.0.1:8765 UZYTKOWNIK@ADRES_SERWERA
```

Otworzyć `http://127.0.0.1:8765`. Transmisja między komputerem a serwerem
jest prowadzona szyfrowanym tunelem SSH; lokalny adres HTTP nie jest
publicznym adresem strony. Nie wystawiać tego demo przez publiczne proxy.
Dostęp do kont i SSH przyznawać wyłącznie wybranym testerom. Nie udostępniać
klucza administracyjnego VPS ani pliku wszystkich kont publicznie.

Osoba uruchamiająca podgląd może odczytać konta w swoim prywatnym pliku.
Hasła nie powinny trafiać do raportów, zrzutów ekranu, czatu ani repozytorium.
Ten pakiet nie wysyła haseł żadnym testerom.

## Zakończenie i odbiór

Ctrl+C w terminalu podglądu kończy proces i usuwa utworzony plik kont.
Launcher usuwa tylko plik o tej samej tożsamości, który sam utworzył;
nie usuwa podmienionego pliku. Po twardym zabiciu procesu lub awarii systemu
sprzątanie nie jest zagwarantowane; sprawdzić pozostałości w prywatnym
katalogu przed następnym uruchomieniem. Nie usuwać przypadkowych istniejących
plików, aby obejść odmowę nadpisania.

Odbiór obejmuje logowanie czterech ról, katalog, koszyk, pojedynczą opłatę
za przesyłkę, PIN i prywatne zgłoszenia. Restart tego demo tworzy nowe konta
i nowe dane. Testy trwałości PostgreSQL nie są zastępowane tym scenariuszem.

## Potwierdzona weryfikacja lokalna — 18.10.2026

26 zaliczonych, 0 błędów, 0 pominiętych w zestawie:
`test_preview_credentials.py`, `test_sample_demo_launcher.py`,
`test_phone_demo_launcher.py`, `test_deployment_guard.py`.

Nowy test uruchamia rzeczywisty proces na loopback, pobiera stronę i zdrowie,
loguje klienta oraz zatrzymuje grupę procesów SIGINT. Potwierdza brak haseł
i adresów kont w stdout/stderr oraz usunięcie prywatnego pliku.
Pozostałe przypadki sprawdzają uprawnienia 0600, odmowę użycia współdzielonego
katalogu, odmowę nadpisania pliku i symlinku, sprzątanie po wyjątku i zachowanie
podmienionego pliku. Obsługa prywatnego pliku jest wyłącznie POSIX;
dotychczasowy lokalny launcher Windows pozostaje dostępny bez tej opcji.
Nie wykonywano rzeczywistego połączenia SSH ani instalacji na VPS.

Po dodaniu do bramki CI: 63 zaliczone, 0 błędów, 0 pominiętych w powyższych
modułach oraz `test_native_ci_runner.py` i `test_native_gate_schema_review.py`.
Zestaw 26 przypadków jest podzbiorem tych 63; liczb nie należy sumować.
Bramka Chromium wykonuje również 9 testów prywatnego podglądu na Linux.
