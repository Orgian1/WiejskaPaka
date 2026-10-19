# Testowy reset HTTP z zaszyfrowaną kolejką

Stan: 19.10.2026. Istniejące trasy /auth/password-reset-test/request oraz
/auth/password-reset-test/confirm mogą działać w jawnym testowym trybie
kolejki. Dotychczasowa skrzynka plikowa pozostaje osobnym trybem demo.
Nie uruchomiono SMTP ani procesu pracownika. W testach kolejka jest
wykonywana ręcznie przez dispatch_once z transportem w pamięci.

## Konfiguracja

Kolejka HTTP wymaga równocześnie WP_ENV=test/testing,
WP_ENABLE_TEST_PASSWORD_RESET=1, WP_ENABLE_TEST_RESET_QUEUE=1,
WP_ENABLE_MAIL_QUEUE=1 i WP_MAIL_QUEUE_KEYS_FILE wskazującego poprawny
prywatny plik POSIX opisany w KLUCZE_KOLEJKI_POCZTY.md. WP_TEST_RESET_OUTBOX
musi pozostać nieustawiony. Błędny tryb, niepełne flagi lub nieprawidłowe
klucze przerywają start ze stałym, nieujawniającym sekretów błędem.
Nie generować zastępczego klucza przy restarcie.

PostgreSQL wymaga dodatkowo istniejącego opt-in
WP_ENABLE_PG_TEST_PASSWORD_RESET=1 i dedykowanej lokalnej bazy testowej.
Wymagane migracje operator przygotowuje oddzielnie. Aplikacja nie tworzy
na PostgreSQL tabeli kolejki. Włączony tryb wykonuje przy starcie kontrolę
obecności wymaganych kolumn; brak tabeli przerywa start.
SQLite tworzy tabele testowe wyłącznie po jawnym opt-in.

Zwykłe launchery demo i izolowanych testów usuwają odziedziczone flagi
kolejki, poczty i ścieżkę kluczy. Uruchomienie zwykłego demo nie włącza
kolejki ani nie tworzy jej tabeli. Flagi nie włączają prawdziwego SMTP.

## Przebieg żądania

Żądanie HTTP zapisuje hash tokenu, limity i zaszyfrowane zadanie w jednej
transakcji. Odbiorca pochodzi z konta. Nieznany adres nie otrzymuje zadania.
Nie powstaje plik JSON z jawnym linkiem. Potwierdzenie wykorzystuje ten sam
protokół jednorazowego tokenu i cofania sesji co dotychczasowy reset.

Dla poprawnego żądania odpowiedź ma ogólną treść i HTTP 202/no-store,
niezależnie od istnienia konta, limitu lub błędu zapisu. Błąd bazy cofa
transakcję i zapisuje wyłącznie stały komunikat diagnostyczny, bez danych
odbiorcy, tokenu, kluczy i odpowiedzi bazy. Odpowiedź nie zawiera linku,
identyfikatora zadania lub stanu transportu. Walidacja struktury żądania
nadal może zwrócić HTTP 422; wyłączony reset zwraca HTTP 404.

Odpowiedź HTTP nie dowodzi wysłania lub dostarczenia wiadomości. Kolejka
oczekuje na osobno uruchomione wykonanie. W tym etapie nie ma harmonogramu,
pętli pracownika ani wywołania adaptera SMTP z żądania HTTP.

## Zakres odbioru

Testy SQLite używają rzeczywistego serwera HTTP i obejmują pełny reset przez
podstawiony transport, brak pliku z linkiem, restart, limity równoległych
żądań, rollback po wymuszonym błędzie zapisu i odmowę startu przy złej
konfiguracji. Natywne testy PostgreSQL sprawdzają ponadto ten sam przepływ
przy ograniczonej roli, błąd transakcji i brak migracji podczas restartu.

Pozostają integracja i odbiór pracownika, potwierdzanie adresów, retencja,
operacyjne przygotowanie oraz kopie kluczy, próba odtworzenia i odbiór
rzeczywistego dostawcy. Odpowiedź ogólna nie gwarantuje stałego czasu
przetwarzania. Ten tryb jest prywatnym testem, nie publicznym uruchomieniem
odzyskiwania hasła lub dopuszczeniem do produkcji.
