# Wykonywanie kolejki PostgreSQL i prywatne klucze — 19.10.2026

Kod połączony: 60526b06681e3f54a58b1a2a5638adbf40d0127f.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39216884076
PR: https://github.com/Orgian1/WiejskaPaka/pull/9

## Zrealizowany zakres

Odłączony moduł kolejki resetu wykonuje teraz operacje na PgConnection.
Własne krótkie transakcje, FOR UPDATE SKIP LOCKED podczas przejmowania
oraz odzyskiwania i blokowanie wiersza przy starcie oraz wyniku chronią
przed konkurencyjnym wykonaniem. Transport jest wywoływany po trwałym
zapisie znacznika próby, bez utrzymywania blokady wiersza. Odzyskanie
rozpoczętej próby nie powoduje ponowienia niepewnego wysłania.

Osiem nowych scenariuszy natywnych obejmuje wykonanie, rollback po błędzie
SQL, nieznanego odbiorcę i limity, czterech równoległych pracowników,
odzyskiwanie dzierżaw, pomijanie zablokowanych także wygasłych wierszy,
unieważnienie przez reset oraz ograniczone ponowienia. Każdy scenariusz
korzysta z osobnej jednorazowej bazy i ograniczonej roli aplikacji. Bramka
wymaga co najmniej 36 zaliczeń zamiast 28.

Osobny loader jawnie odczytuje wersjonowane klucze z prywatnego pliku POSIX.
Sprawdza właściciela, prawa, rodzaj pliku, limit 16 KiB, jednoznaczny format
JSON i klucze 256-bitowe w kanonicznym Base64. Odrzuca duplikaty, nieznaną
aktywną wersję i błędny format. Domyślnie jest wyłączony i nie tworzy klucza
zastępczego. Stały błąd nie zawiera ścieżki, fragmentu pliku lub parsera.
Test rotacji odczytuje wcześniejsze zadanie po ponownym załadowaniu kluczy.

Dokumentacja: KOLEJKA_RESETU_POSTGRESQL.md i KLUCZE_KOLEJKI_POCZTY.md.
Nie dodano nowej migracji: wykorzystano tabelę z poprzedniego pakietu.

## Weryfikacja

Pakiet kontrolny połączonego kodu: 112 zaliczonych, 1 pominięty. Pominięcie
na Linuxie dotyczy odmowy działania na systemie innym niż POSIX. Testy
uprawnień plików na Windows są jawnie pomijane; loader odmawia tam odczytu.
Wyniki kontrolne nakładają się na pełną regresję i nie są do niej doliczane.
Dodatkowa lokalna próba 2000 odmów odczytu niebezpiecznych plików
(publiczne prawa, dowiązanie, FIFO i katalog) zachowała liczbę deskryptorów
4 przed i 4 po próbie. Błędy miały wyłącznie stały kod bez prywatnych danych.
Ta próba zasobów również nie jest doliczana do testów regresji.

| Bramka połączonego kodu | Zaliczone | Błędy | Pominięte | Stan |
| --- | ---: | ---: | ---: | --- |
| Pełny Linux, 320/320 modułów | 3976 | 0 | 59 | sukces |
| Pełny Windows | — | — | — | w toku |
| PostgreSQL 16 | 36 | 0 | 0 | sukces |
| Chromium i HTTP | 36 | 0 | 0 | sukces; HTTP w pięciu rozmiarach |
| Szybki Windows | 80 | 0 | 0 | sukces |

Dowody połączonego kodu: audits/mail_keys_60526b0_2026-10-19/.
Osobny katalog pg_queue_1ed505f_2026-10-19 dokumentuje etap kolejki sprzed
loadera; jego raportów nie przedstawiać jako testów połączonego kodu.
Pełny Linux tego wcześniejszego etapu zaliczył 3946 przypadków, bez błędów,
z 58 pominięciami i wykonaniem 319/319 modułów.
Artefakty CI są weryfikowane przez SHA-256 archiwum, zgodność odcisków
źródeł, success, complete i sources_unchanged.

## Granice i następny etap

Moduły nie są wywoływane przez trasy aplikacji i nie mają uruchomionego
pracownika. Zmienne loadera pozwalają wyłącznie odczytać klucze przy jawnym
wywołaniu funkcji; samo ich ustawienie nie uruchamia poczty. Transport
natywnych testów jest zastąpiony funkcją w pamięci. Nie wysłano wiadomości.

Pozostają ogólny bezpieczny endpoint HTTP, potwierdzanie adresów, retencja
metadanych, ograniczony proces pracownika i odbiór jego uprawnień,
prywatne przygotowanie oraz rotacja kluczy, ich kopia i próba odtworzenia,
a także osobny odbiór dostawcy poczty i DNS. Istniejąca kopia bazy z kluczem
sejfu nie zawiera wersjonowanych kluczy poczty. Import kopii nie może
samodzielnie uruchamiać wysyłek historycznych zadań.

Hosting i rzeczywiste płatności pozostają niepodłączone. Rolnik i sprzedawca
pozostają tą samą rolą. To odbiór wyznaczonego zakresu testowego, nie zgoda
na sprzedaż produkcyjną.
