# Izolacja wszystkich trybów demonstracyjnych

Podstawowe demo i `--sample-data` usuwały wybrane ustawienia bazy i kolejki,
ale dziedziczyły pozostałe zmienne procesu, w tym ustawienia SMTP, sekrety
usług i nieznane flagi. Samodzielny `scripts.demo_journey` usuwał tylko kilka
adresów baz: przy odziedziczonym trybie produkcyjnym aplikacja odmawiała startu,
a opcjonalne reguły dostaw mogły zmienić scenariusz demonstracyjny.

## Zmiana

Każdy profil serwera lokalnego dziedziczy teraz wyłącznie ustawienia systemowe
potrzebne do uruchomienia Pythona i sześć znanych lokalnych funkcji: jednostki,
zdjęcia, wyszukiwanie sprzedawców, dostawy adresowe, terminy odbioru i portfel.
Nie dziedziczy adresów baz, sekretów usług, konfiguracji poczty, PYTHONPATH
ani nowych, nieznanych flag. Baza i tryb development są ustawiane jawnie.
Nie zmieniono konfiguracji właściwego serwera ani istniejących integracji.

`--full-demo` nadal włącza wszystkie sześć funkcji, fikcyjne konta czterech ról
i symulator płatności; `--sample-data` nadal przygotowuje podstawowe dane.
Lokalna skrzynka resetu jest ustawiana jawnie dopiero przez launcher.
Wszystkie warianty pozostają na 127.0.0.1 i usuwają dane po zakończeniu.

Samodzielny scenariusz zakupowy używa stałego profilu podstawowego:
nie dziedziczy opcjonalnych reguł zakupu ani trybu produkcyjnego. Zmiana
środowiska odbywa się przed importem backendu w jego osobnym procesie.

## Rzeczywista weryfikacja

Dwa przypadki regresyjne przed poprawką zakończyły się błędem: zachowanie
konfiguracji usług oraz odrzucenie startu przez odziedziczony tryb produkcyjny.
Po poprawce wykonano 59 testów w 16 modułach: 59 PASS, 0 FAIL, 0 SKIP.
Obejmują prawdziwe przygotowanie kont i zamówień, restart HTTP, odzyskiwanie
po awarii zakupu, koszyk wielu sprzedawców, podgląd mobilny, reset i gotowość demo.
Samodzielne `python -m scripts.check_demo_readiness` również zakończyło się sukcesem.
Nie wysyłano poczty; ustawienia usług w regresjach były wyłącznie syntetyczne.

Pierwsza pełna regresja ujawniła również cztery testy HTTP zależne od
dziedziczonej flagi wymagania potwierdzonego e-maila. Serwer testowy przyjmuje
teraz tę opcję jawnie wraz z testowym kluczem, zamiast pobierać ją z otoczenia.
Nie poluzowano izolacji demo. Po tej poprawce 17 testów HTTP potwierdzenia,
kolejki i restartu zakończyło się sukcesem.

Kod końcowy: `064ab859412015f0f6d58fc2fb059d75ec8d47ed`.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/42805536971.
Wynik pełnego CI: **5/5 zadań — sukces** dla `064ab85`.

| Bramka | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Windows — pełna izolowana regresja | 4642 | 0 | 275 |
| Windows — szybka regresja | 91 | 0 | 0 |
| PostgreSQL 16 | 97 | 0 | 0 |
| PostgreSQL 17 | 97 | 0 | 0 |
| Chromium — zdjęcia i scenariusze offline | 76 | 0 | 0 |

Windows: 4917 przypadków, bez niekompletnych modułów i timeoutów.
275 pominięć nie jest zaliczeniami. Oba dodatkowe kroki z poprzedniego
pakietu czatu — gotowość i nagłówek oraz izolowana ścieżka zakupowa —
również zaliczone. Każdy z pięciu artefaktów potwierdza sukces, zakończenie
i niezmienność źródeł; sprawdzono zgodność odcisków i sum archiwów GitHuba.
Raport końcowy zmienia wyłącznie dokumentację; wyniki dotyczą kodu `064ab85`.

Końcowa pełna regresja lokalna zakończona, 387/387 modułów, bez zmiany źródeł:
4756 PASS, 61 FAIL, 100 SKIP (łącznie 4917). Wszystkie 61 błędów w 16 modułach
dotyczy uruchomienia Chromium: środowisko blokuje socket AF_UNIX przez
Operation not permitted. Nie przedstawiać tego przebiegu jako pełnego sukcesu.
Żaden inny moduł nie zakończył się błędem. Rzeczywisty Chromium w końcowym CI
zaliczył 76 testów i HTTP w pięciu rozmiarach widoku.

Artefakty: `audits/demo_environment_isolation_2026-11-10/`.
Podkatalog `preliminary/` zawiera wcześniejsze, wyraźnie oznaczone wyniki
dla `5a12b65`; końcowy przebieg CI zastąpił jego nieukończony Windows.
Nie sumować liczników bramek: część testów jest uruchamiana w kilku profilach.

## Gałęzie i wdrożenie

PR #54 bazuje na końcowym #53 (`3e5d026`). Zawiera również wcześniejsze zmiany
zwykłego czatu z #50. Próbna integracja historii main ma commit
`f2d27a89626f341d32e366a50b30c36ecbf65cc2`, z drzewem identycznym jak kod #54.
Nie zmieniono main, wcześniejszych gałęzi PR-ów, VPS ani jego danych.

Nie dodano migracji; wymagania migracji portfela z #52–53 pozostają w mocy.
Nie uruchamiać starszego kodu portfela z nowymi danymi bez opisanej ochrony
blokad operacji i warunków wypłat. Wdrożenie i rollback:
`WDROZENIE_I_WYCOFANIE_DEMO_2026-11-10.md`.

Brak zweryfikowanego dostępu i aktualnego odczytu VPS nadal uniemożliwia
wdrożenie w tej sesji. Portfel i płatności zamówień pozostają oddzielnymi
symulacjami. Nie podłączano PayU, banku ani rzeczywistych płatności.
