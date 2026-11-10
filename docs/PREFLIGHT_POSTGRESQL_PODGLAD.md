# Kontrola PostgreSQL przed zamkniętym podglądem

Narzędzie `scripts/check_postgres_preview.py` sprawdza konfigurację, czytelność
osobnego klucza sejfu oraz podstawowy schemat i rolę PostgreSQL przed startem
usługi. Nie uruchamia serwera, migracji, rejestracji, płatności ani backupu.

## Wymagane przygotowanie

- Osobna lokalna baza testowa PostgreSQL z wcześniej sprawdzonymi migracjami.
  Nie używać Neon, bazy produkcyjnej ani prawdziwych danych użytkowników.
- Ograniczona rola aplikacji: bez SUPERUSER, BYPASSRLS, CREATEDB i CREATEROLE.
- Zachowany klucz sejfu poza repozytorium, pod bezwzględną ścieżką; tylko
  właściciel ma dostęp na POSIX. Klucz nie może być dowiązaniem symbolicznym.
  Można go przygotować istniejącym `scripts/checkout_keys.py`.
- WP_ENV=test, wyłączone prawdziwe płatności, brak WP_AUTO_INIT_POSTGRES,
  brak konfiguracji SQLite i brak sprzecznego DATABASE_URL.

Nie generować nowego klucza przy każdym restarcie trwałej bazy. Istniejący
klucz i jego chroniona kopia są potrzebne do odczytu zaszyfrowanych odpowiedzi.
Ta kontrola sprawdza format i dostępność klucza, nie jego zgodność z każdym
zaszyfrowanym rekordem. Ta zgodność wymaga odrębnego testu odtworzenia.

## Uruchomienie lokalnie na serwerze

Użyć środowiska wirtualnego projektu i istniejącego pliku klucza. W Bash
można podać URL bazy bez zapisywania go w historii poleceń:

```bash
export WP_ENV=test
read -r -s -p 'URL lokalnej bazy testowej: ' WP_TEST_DATABASE_URL
printf '\n'
export WP_TEST_DATABASE_URL
read -r -p 'Bezwzględna ścieżka istniejącego klucza: ' WP_CHECKOUT_KEY_FILE
export WP_CHECKOUT_KEY_FILE
.venv/bin/python scripts/check_postgres_preview.py
unset WP_TEST_DATABASE_URL WP_CHECKOUT_KEY_FILE
```

Nie podawać hasła w argumencie programu, w repozytorium lub w czacie.
Kontrola akceptuje wyłącznie loopback/localhost dla bazy. To dodatkowe
ograniczenie narzędzia, niezależne od transportów obsługiwanych przez aplikację.
Sam program nie usuwa cudzych zmiennych, plików ani danych.

## Wynik

JSON zawiera wyłącznie ustalone nazwy pól, wartości logiczne i ogólny kod
błędu. Nie zawiera DSN, nazwy bazy, użytkownika, hosta, ścieżki lub treści
klucza i surowego komunikatu sterownika. Kod zakończenia 0 oznacza zaliczenie
tej kontroli; 1 oznacza odmowę lub błąd.

- CONFIGURATION_REJECTED: niespójne lub niedozwolone ustawienia.
- CHECKOUT_KEY_REJECTED: klucz niedostępny, niewłaściwy albo wewnątrz projektu.
- DATABASE_PROBE_FAILED: połączenie, tożsamość bazy, rola lub rdzeń schematu
  nie przeszły kontroli. Dokładną przyczynę administrator ustala prywatnie.

Połączenie dostaje wymuszony domyślny tryb transakcji tylko do odczytu,
limit zapytania 5 s i oczekiwania na blokadę 1 s oraz search_path=pg_catalog.
Opcje te nie są dziedziczone z PGOPTIONS. Połączenie jest zamykane także
po błędzie. Odczyty obejmują metadane, bez pobierania zamówień lub kont.

## Granice wyniku

`success=true` nie oznacza gotowości hostingu lub produkcji. Sprawdzany jest
rdzeń schematu z `CORE_TABLES`; nie pełny kontrakt kolumn, indeksów, sekwencji,
uprawnień każdej tabeli ani polityk RLS. Nie jest to dowód skalowania,
odporności, kompletności backupu lub zgodności prawnej.
`ready_for_production`, `preview_started` i `backup_restore_verified`
pozostają false także po sukcesie. Dopiero późniejszy start aplikacji i test
rzeczywistych operacji sprawdzają jej dalsze wymagania schematu.

## Weryfikacja pakietu — 18.10.2026

Lokalny zestaw celowany: 80 zaliczonych, 0 błędów, 0 pominiętych; obejmuje
nową kontrolę, guard trybu, kontrolę schematu, reporter CI i poprzedni podgląd
SSH. Nie sumować go z wcześniejszymi zestawami, które się pokrywają.

Do natywnej bramy PostgreSQL dodano osobny scenariusz na losowej bazie i
ograniczonej roli istniejącego fixture. Sprawdza rzeczywiste
SHOW transaction_read_only=on i wynik narzędzia. Bramka wymaga teraz minimum
19 przypadków bez pominięć. Wynik tego scenariusza należy odczytać z CI dla
konkretnego commitu; lokalne makiety nie stanowią wykonania PostgreSQL.
Nie podłączono zewnętrznego serwera ani bazy i nie wykonano wdrożenia.
