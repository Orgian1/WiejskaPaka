# WiejskaPaka — raport pakietu demonstracyjnego bez PayU

Data: 10.11.2026. Zmiany: PR #51, gałąź `preview/demo-completion-20261110`.
Wersja kodu: `90f9b5fbaacf792a995bf263e85f37b5dc09fbbe`.
Baza: wskazany przez właściciela commit `ecd0c8d9163845ee86aaf4226d1be7c1deeeb533` z PR #50.

## Stan gotowości

Wszystkie **5/5 zadań GitHub Actions zakończone sukcesem** dla podanej wersji
kodu. Lokalne demo jest gotowe do końcowej kontroli w opisanym poniżej zakresie.
Wdrożenie na VPS nie zostało wykonane ani potwierdzone. Portfel i płatności
zamówień pozostają osobnymi symulacjami, co opisano w granicach gotowości.

## Wykonane zmiany

- Jeden start `python scripts/run_phone_demo.py --full-demo` przygotowuje
  cztery losowe konta, dwie oferty, punkt, datę obecności, publiczny login
  sprzedawcy oraz przesyłki odbiorową i dostawczą. Profil włącza sześć funkcji:
  portfel, jednostki, zdjęcia, wyszukiwanie sprzedawców, kalendarz punktu,
  terminy dostaw. Dostawa ma zaakceptowane okno i jedną opłatę 501 gr.
- Profil przenosi z otoczenia tylko jawnie wymienione ustawienia uruchomieniowe
  systemu. Nie kopiuje PayU, DSN, SMTP, workerów, zewnętrznych kluczy ani PYTHONPATH.
  Używa nowej SQLite w prywatnym katalogu, a nie poprzednich danych.
- Portfel pokazuje wycenę wypłaty: sprzedawca 5%, klient 0%; prowizja jest
  zawarta w całej rezerwowanej kwocie. API wylicza ją wspólną funkcją
  całkowitoliczbową half-up. Formularz pokazuje kwotę po potrąceniu przed
  potwierdzeniem PIN-em, a historia pokazuje tę samą wycenę.
- Naprawiono lukę w kontroli integralności: uszkodzony starszy zapis salda
  mógł przejść, jeżeli końcowe saldo i sumy były poprawne. Kontrola jednego
  spójnego odczytu sprawdza teraz kolejne zapisy salda i rezerwy w dzienniku;
  niespójność blokuje następną zmianę. Nie naprawia danych automatycznie.
- Dodano testy granic zaokrągleń, odrzucania błędnych kwot, prowizji obu ról,
  trwałości po restarcie, ponowień bez podwójnej rezerwacji i uszkodzeń historii.
  Dodano też testy pełnego profilu i ośmiu kombinacji rola/rozmiar w Chromium.
- Nie dodano migracji. Zachowano wcześniejsze API, dane i role.

## Sprawdzenie gałęzi i przygotowanie połączenia

`main` ma inną historię i zawiera tylko początkowy README. Pełna aplikacja jest
w łańcuchu gałęzi kończącym się PR #50; #51 bazuje bezpośrednio na #50.
Sprawdzono lokalne referencje z repozytorium. Starsze rozbieżne ścieżki resetu
zastąpiła wersja v2, a diagnostyczna gałąź zdjęć pozostaje pomocnicza.
Nie wykonywano force-push ani zamykania/scalania wcześniejszych PR-ów.

W osobnym worktree wykonano próbne połączenie historii `main` i wersji demo.
Jedyny konflikt README rozwiązano zachowując pełną instrukcję aplikacji.
Wynikowy tree SHA `f3c1b38c98822f2c99882a5e7949aa3645e55956` jest identyczny
z drzewem kodu #51. Żaden plik aplikacji nie zniknął. Próba nie zmieniła main.
Jej zapis na GitHubie: `integration/demo-main-20261110`, commit
`3e9251301a598016b9b226619f88d43c6d9ba76e` (dwóch rodziców, identyczne drzewo kodu).
Szczegółowa mapa: `GALEZIE_DEMO_2026-11-10.md`.

## Wyniki testów

CI dla kodu `90f9b5f`: https://github.com/Orgian1/WiejskaPaka/actions/runs/42760458719.

| Zestaw | Wynik | Uwagi |
| --- | --- | --- |
| PostgreSQL 16 | 84 PASS, 0 FAIL, 0 SKIP | natywna baza, ograniczona rola, rzeczywisty HTTP i restart |
| PostgreSQL 17 | 84 PASS, 0 FAIL, 0 SKIP | te same bramki na drugiej wersji PostgreSQL |
| Szybki Windows | 80 PASS, 0 FAIL, 0 SKIP | demo, odzyskiwanie i rozliczenia |
| Chromium | 66 PASS, 0 FAIL, 0 SKIP + HTTP na 5 rozmiarach | 2 zdjęcia, 64 scenariusze ról i formularzy; 320/360/390/768/1280 px w kontroli HTTP |
| Pełny Windows | 4603 PASS, 0 FAIL, 252 SKIP | 4855 przypadków, brak niekompletnych modułów i timeoutów |
| Pełny lokalny Linux | 4717 PASS, 51 błędów startu Chromium, 87 SKIP | 4855 przypadków w 382 modułach; źródła niezmienione |

Lokalne 51 błędów pochodzi wyłącznie z 14 modułów przeglądarkowych, które
zatrzymały się na `socket() failed: Operation not permitted`. Nie oznaczono
lokalnego przebiegu jako sukcesu. Te ścieżki wykonano następnie w natywnej
bramce Chromium CI, która przeszła bez błędów i bez pominięć. Pominięcia lokalne
obejmują m.in. nieudostępnioną natywną bazę; PostgreSQL zweryfikowano w CI.

Zaliczone dodatkowo: scenariusz `check_demo_readiness`, JavaScript `node --check`,
38/38 sum kontrolnych migracji i brak konfliktów nowego diffu. Kontrola manifestu
nie wykonuje migracji. Raporty maszynowe: `audits/demo_no_payu_2026-11-10/`.
Odciski aplikacji, testów, zależności i workflow lokalnie oraz we wszystkich pięciu
pobranych raportach natywnych są zgodne. Końcowy zapis dokumentów i JSON nie
zmienia backendu, interfejsu, skryptów, migracji, zależności ani testów względem
commitu kodu. Jest osobnym commitem dokumentacyjnym z pominięciem ponownego CI. Zestawy częściowo się pokrywają; nie sumować
ich liczników jako liczby różnych testów.

## Zakres kontroli

| Obszar | Weryfikacja |
| --- | --- |
| Rejestracja, logowanie, sesje | HTTP, prywatność sesji, blokady, reset hasła, wylogowanie, izolacja kont |
| Katalog i produkty | wyszukiwanie, publiczny login, jednostki, zdjęcia, magazyn, równoległe zakupy |
| Koszyk i zamówienia | ponowienia, wiele produktów i sprzedawców, niezmienny zapis zakupu, jedna dostawa na paczkę |
| Punkt, PIN, dostawca | odbiór całej przesyłki, PIN, odmowa nieuprawnionych operacji, prywatność adresu po odbiorze |
| Dostawa i zwroty | termin/akceptacja/odrzucenie, anulowanie, przywrócenie magazynu, scenariusze zwrotów testowych |
| Portfel | grosze, PIN, blokady, prowizja 5%/0%, historia, restart, ponowienia, współbieżność, rollback przy błędzie |
| Sprzedawca i administrator | profile i przegląd, licznik zakończonych transakcji, zgłoszenia, raporty i CSV |
| Powiadomienia | lokalny reset hasła, syntetyczny transport, kolejki, dowód adresu, duplikaty, awarie i kwarantanna po restore |
| Komputer i telefon | Chromium: role, formularze i widoki responsywne; bez testu na fizycznym urządzeniu |

## Granice gotowości i pozostałe czynności

- Brak zweryfikowanego dostępu SSH i odczytu bieżącego stanu VPS w tej sesji.
  Nie wykonano wdrożenia, backupu VPS ani próby odtworzenia jego danych.
  Procedura wraz z rollbackiem: `WDROZENIE_I_WYCOFANIE_DEMO_2026-11-10.md`.
- Nowy profil jest lokalny i jednorazowy; nie stanowi trwałego hostingu.
- Portfel jest osobną symulacją. Nie opłaca zamówień, nie otrzymuje przychodów
  ani zwrotów z ich osobnego symulatora; wnioski wypłat są pending i nie robią
  przelewu. Wycenę prowizji wylicza stała polityka preview także dla starszej
  historii. Nie jest to niezmienny zapis rzeczywistego potrącenia operatora.
- Poczta zewnętrzna nie była wysyłana. Nowy lokalny profil nie uruchamia
  weryfikacji e-maila ani workerów; te mechanizmy mają oddzielne testy syntetyczne.
- Całkowite ilości jednostek są dostępne w zakupie. Ułamkowe zakupy pozostają
  poza aktualnym przepływem, jak przed tym pakietem.
- PayU, rzeczywiste płatności i operacje na rzeczywistych środkach nie były
  podłączane ani wykonywane. Gotowość demo nie jest gotowością płatności live.

Instrukcja uruchomienia i końcowej kontroli: `DEMO_BEZ_PAYU_2026-11-10.md`.
