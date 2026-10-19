# Reset HTTP z zaszyfrowaną kolejką — 19.10.2026

Kod: 8caa2817d88e35e1b19ef7f709c7db0705a2397b.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39222927451
PR: https://github.com/Orgian1/WiejskaPaka/pull/10

## Zrealizowany zakres

Istniejący prywatny testowy reset HTTP ma jawny wariant kolejki. Żądanie
zapisuje hash tokenu, limit i zaszyfrowane zadanie w jednej transakcji.
Nie tworzy pliku z jawnym linkiem. Odbiorca pochodzi z zapisanego konta;
nieznany adres nie otrzymuje zadania. Odpowiedź 202/no-store jest ogólna
również przy limicie i błędzie zapisu; wyjątek bazy powoduje rollback oraz
wyłącznie stały komunikat diagnostyczny bez danych użytkownika lub sekretów.

Pełny opt-in wymaga testowego środowiska, flag resetu i kolejki oraz poprawnego
prywatnego pliku kluczy. Łączenie z testowym filebox jest odrzucane. PostgreSQL
wymaga dodatkowego lokalnego opt-in i przygotowanej migracji. Brak tabeli
przerywa start; aplikacja nie tworzy jej na PostgreSQL. Launchery usuwają
odziedziczone flagi kolejki i poczty oraz ścieżkę prywatnych kluczy.

Dotychczasowy reset ze skrzynką plikową pozostaje osobnym trybem. Potwierdzenie
linku wykorzystuje wspólny protokół jednorazowości i cofania sesji. Nie dodano
wywołania SMTP ani pracownika w tle. Instrukcja: RESET_HASLA_KOLEJKA_HTTP_TEST.md.

## Kontrola funkcjonalna

Pakiet nowej konfiguracji, HTTP i runnera: 53 zaliczone testy. Osobno 19 testów
dotychczasowego resetu i konfiguracji PostgreSQL zakończono sukcesem. To
podzbiory pełnej regresji, nie dodatkowe liczby do jej sumowania.

Cztery nowe scenariusze natywne obejmują pełny przepływ po restarcie API,
równoległe żądania, wymuszony błąd transakcji i odmowę startu bez tabeli.
Każdy używa osobnej lokalnej testowej bazy z ograniczoną rolą. Transport jest
zastąpiony funkcją w pamięci. Natywna bramka wymaga teraz 40 zaliczeń.

Dodatkowa próba rzeczywistego restartu SQLite/API po rotacji aktywnego klucza
potwierdziła oczekujące zadania z wersjami v1 i v2. Oba odczytano przez
podstawiony transport. Potwierdzenie jednego linku zwróciło 200, drugiego
po tym resecie 400. To próba testowego przepływu, nie rzeczywistego dostarczenia.
Nie jest doliczana do regresji.

## Wyniki bramek

| Bramka | Zaliczone | Błędy | Pominięte | Stan |
| --- | ---: | ---: | ---: | --- |
| Pełny Linux, 322/322 modułów | 3997 | 0 | 63 | sukces |
| Pełny Windows | — | — | — | w toku |
| PostgreSQL 16 | 40 | 0 | 0 | sukces |
| Chromium i HTTP | 36 | 0 | 0 | sukces; HTTP w pięciu rozmiarach |
| Szybki Windows | 80 | 0 | 0 | sukces |

Dowody: audits/queued_http_8caa281_2026-10-19/. Artefakty CI mają sprawdzony
SHA-256 archiwum, zgodność odcisków źródeł, success, complete oraz
sources_unchanged. Pominięcia są wykazane oddzielnie.

## Następny etap

Tryb pozostaje prywatnym testem. Odpowiedź HTTP nie potwierdza dostarczenia,
a ogólna treść nie stanowi gwarancji stałego czasu przetwarzania.
Nie uruchomiono dostawcy SMTP, harmonogramu ani procesu pracownika.
Pozostają odbiór pracownika, potwierdzanie adresów, retencja, operacyjne
przygotowanie i kopie kluczy, próba odtworzenia, obserwacja błędów oraz
osobny odbiór dostawcy i DNS. Istniejąca kopia bazy z kluczem sejfu nie
zastępuje kopii kluczy poczty; odtworzenie danych nie może samo uruchamiać
wysyłek historycznych zadań.

Hosting i rzeczywiste płatności pozostają niepodłączone. Rolnik i sprzedawca
są tą samą rolą. Ten raport dotyczy wyznaczonego zakresu testowego,
nie uruchomienia publicznego odzyskiwania hasła lub sprzedaży produkcyjnej.
