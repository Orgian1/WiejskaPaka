# Checkpoint retencji kolejki — 19.10.2026

Kod: 30a632f2a2814027294be3ce02df7bae511e3225.
Gałąź: preview/reset-queue-retention-20261019.
Roboczy PR: https://github.com/Orgian1/WiejskaPaka/pull/14
Baza: preview/bounded-reset-worker-20261019 (PR #13; wcześniej PR #12).
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39276035351

## Zakres

Jawne usuwanie starych metadanych zakończonych zadań w ograniczonej partii,
z transakcją i FOR UPDATE SKIP LOCKED na PostgreSQL. Nie usuwa queued/leased,
ich ładunków, tokenów, sesji ani danych zakupów. Nie uruchamia automatycznej
retencji ani transportu. Szczegóły: RETENCJA_KOLEJKI_POCZTY.md.

## Weryfikacja badanego kodu

| Bramka | Wynik |
| --- | --- |
| Pełny Linux, 323/323 modułów | 4021 PASS, 0 FAIL, 65 SKIP |
| Natywny PostgreSQL 16 | 42 PASS, 0 FAIL, 0 SKIP |
| Chromium | 36 PASS, 0 FAIL, 0 SKIP; HTTP w pięciu rozmiarach: sukces |
| Szybki Windows | 80 PASS, 0 FAIL, 0 SKIP |
| Lokalny pakiet kontrolny | 127 PASS, 0 FAIL, 38 SKIP (bez lokalnego PostgreSQL) |
| Pełny Windows retencji | W trakcie przy ostatnim odczycie; nie przedstawiać jako zaliczony |

Pakiet kontrolny nakłada się na pełną regresję; nie sumować wyników.
Dowody: audits/queue_retention_30a632f_2026-10-19/. Wszystkie cztery
lokalne części zakończone, z niezmienionymi źródłami i jednym odciskiem
aplikacji. Zapisano odciski modułów i ich liczniki. Raporty natywne
zweryfikowano przez SHA-256 archiwów, zgodność wszystkich odcisków
źródeł/testów/zależności i complete/success/sources_unchanged.
Drzewo lokalnego i zdalnego kodu jest identyczne:
32d45d2072e71dff7a789f2eb299535f3297b823.

## Zamknięte zaległe bramki

Odebrano obie wcześniejsze pełne regresje Windows i zapisano zweryfikowane
raporty: HTTP 3931 PASS, 0 FAIL, 119 SKIP (88c4cad); pracownik 3950 PASS,
0 FAIL, 120 SKIP (f4ddd02). Są to wyniki wcześniejszych commitów, a nie
regresja nowej retencji. Checkpoint pracownika zaktualizowano.

## Następny punkt pracy

Najpierw odebrać pełny Windows z przebiegu 39276035351 i zweryfikować
artefakt windows-summary względem raportu PostgreSQL tego samego commita.
Nie porównywać odcisków wcześniejszego przebiegu z później zmienionym kodem.
Następnie: potwierdzanie adresów, bezpieczna kopia/rotacja kluczy i próba
odtworzenia, osobne konto/rola/usługa pracownika oraz nadzorca procesu.
Dla dużych tabel pozostają pomiar retencji i dobór indeksu — limit partii
ogranicza liczbę usunięć, nie koszt skanowania. Konfiguracja retencji jest
techniczna; nie określa prawnego okresu przechowywania danych.

Nie scalono PR #12–14. Nie podłączono prawdziwej poczty, hostingu ani
rzeczywistych płatności. Pracownik i retencja pozostają jawnie wywoływane.
