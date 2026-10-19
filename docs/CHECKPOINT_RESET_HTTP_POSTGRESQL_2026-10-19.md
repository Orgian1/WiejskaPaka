# Kolejka resetu: natywny odbiór HTTP — 19.10.2026

Zdalny kod: 88c4cad8ede58fe0f97765f0c19655b037638687.
Gałąź: preview/queued-reset-http-v2-20261019.
Roboczy PR: https://github.com/Orgian1/WiejskaPaka/pull/12
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39253492205

Użytkownik wyraził zgodę na wysłanie zmian na GitHub. Kod HTTP z poprzedniego
checkpointu oraz nowy pakiet testów są zapisane na osobnej zdalnej gałęzi.
Nie scalono ich z wiejskapaka-import. Publikacja przez integrację GitHub
zachowała identyczne drzewa plików jak lokalny git (sprawdzono tree SHA).
Wcześniejsza blokada publikacji z checkpointu lokalnego została rozwiązana.

## Zrealizowany pakiet

Cztery nowe scenariusze korzystają z osobnych jednorazowych baz PostgreSQL,
ograniczonej roli aplikacji i prawdziwego HTTP przez loopback:

- zapis zaszyfrowanego zadania, nieznany odbiorca, restart, zużycie i odrzucenie
  ponownego linku, unieważnienie sesji i zachowanie danych zamówienia;
- osiem równoległych żądań, limit trzech zadań i trwałość limitu po restarcie;
- wymuszona awaria INSERT: rollback zadania, tokenu i limitów, bezpieczna
  odpowiedź 500 oraz poprawne działanie po usunięciu przyczyny;
- dwa jednoczesne potwierdzenia: dokładnie jeden sukces, drugi link odrzucony.

Wywołanie kolejki po potwierdzeniu nie przekazuje zużytego tokenu do
transportu i usuwa jego zaszyfrowany ładunek. Nie użyto SMTP ani prawdziwych
adresów. Minimalna liczba zaliczeń bramki PostgreSQL wzrosła z 36 do 40.

## Potwierdzona weryfikacja

| Kontrola | Wynik |
| --- | --- |
| Natywny PostgreSQL 16 | 40 PASS, 0 FAIL, 0 SKIP |
| Chromium | 36 PASS, 0 FAIL, 0 SKIP; HTTP w pięciu rozmiarach: sukces |
| Szybki Windows | 80 PASS, 0 FAIL, 0 SKIP |
| Lokalne testy pakietu i runnera | 48 PASS, 0 FAIL, 36 SKIP (brak lokalnego PostgreSQL) |
| Rzeczywiste odmowy startu dla błędnej konfiguracji | 3/3; stały błąd bez prywatnej ścieżki |
| Pełna regresja Windows | W trakcie w momencie zapisu; nie oznaczać jako zaliczona |

Raporty trzech zakończonych bramek są w
`audits/queued_reset_pg_http_88c4cad_2026-10-19/`. Zweryfikowano SHA-256
archiwów pobranych z CI, zgodność wszystkich odcisków źródeł/testów/zależności
z lokalnym drzewem oraz success, complete i sources_unchanged. Pliki
provenance zapisują identyfikator artefaktu, przebiegu i badanego commita.
Nie sumować nakładających się wyników. Wcześniejsza pełna lokalna regresja
HTTP (3987 PASS, 59 SKIP) jest opisana w poprzednim checkpoincie i dotyczy
kodu sprzed rozszerzenia natywnych testów oraz progu runnera CI.

## Dokładny punkt wznowienia

Najpierw sprawdzić końcowy wynik pełnego Windows w przebiegu 39253492205.
Pobrać windows-summary i zweryfikować SHA-256 archiwum oraz odciski źródeł
przed zapisaniem wyniku. Sprawdzić aktualny zdalny HEAD przed nowym zapisem.
Pełna regresja Windows jest zewnętrznym zadaniem CI; nie wymaga komputera
użytkownika. Brak końcowego wyniku nie jest błędem ani zaliczeniem.

Następnie ograniczony proces pracownika, retencja metadanych, potwierdzanie
adresów, kopia/rotacja kluczy i bezpieczna próba odtworzenia. Rzeczywisty
dostawca i DNS wymagają osobnego odbioru. API nadal nie uruchamia pracownika
ani wysyłek. Hosting i rzeczywiste płatności pozostają niepodłączone.
