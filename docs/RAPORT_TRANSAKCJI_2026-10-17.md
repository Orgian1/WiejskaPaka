# WiejskaPaka — autoryzacja transakcji, 17.10.2026

Punkt wyjścia: `8278ded45a7dbd38288db331fa94fb522ff37cea`.
Gałąź lokalna: `wiejskapaka-import`. Poprzednia paczka: `RAPORT_KONTYNUACJI_2026-10-17.md`.

## Odtworzony problem

Niektóre operacje SQLite opierały się na tożsamości odczytanej przez zależność
FastAPI przed rozpoczęciem transakcji. Cofnięcie sesji, jej wygaśnięcie albo
zmiana roli pomiędzy odczytem a zapisem nie blokowały wszystkich modyfikacji.
Dotyczyło to m.in. produktów, punktów, profilu rolnika, koszyka, powiadomień,
przygotowania odbioru, potwierdzenia PIN-em i anulowania.

Nowy zestaw 43 prób wykazał przed poprawką **37 FAIL, 6 PASS**. To wynik
nowych prób wyścigów autoryzacji, odrębny od historycznej regresji Windows.
Próby używają wyłącznie syntetycznych kont i jednorazowego SQLite.
Deterministycznie cofają sesję lub zmieniają jej stan po początkowym odczycie,
ale przed wejściem operacji do transakcji. Osobna próba używa rzeczywistych
wątków: wstrzymany zapis produktu przegrywa z zakończonym wylogowaniem.
Ten nowy wyścig jest sprawdzany przez ASGI TestClient, a nie przez TCP.

## Zmiana

- Wspólny kontekst zapisu SQLite wykonuje teraz kolejno `BEGIN IMMEDIATE`,
  sprawdzenie tokenu i ważności sesji, porównanie bieżącej tożsamości i roli,
  a dopiero potem dopuszcza kod operacji. Wszystko korzysta z jednego połączenia
  i jednej transakcji. Nieważna sesja daje 401; zmieniona rola/tożsamość 403.
- Usunięto powtórne rozpoczynanie transakcji z odbiorców tego kontekstu.
  Kontrola została przeniesiona do wspólnej granicy transakcji, nie usunięta.
  Zachowano dodatkową weryfikację operacji konta po blokadzie konta PostgreSQL.
- Dodanie/usuwanie/czyszczenie koszyka, zapis profilu gospodarstwa i oznaczanie
  powiadomień używają teraz tego samego weryfikowanego kontekstu. Dostały jawny
  parametr nagłówka Authorization; format żądań HTTP klientów pozostaje taki sam.
  Także ścieżka PostgreSQL tych operacji korzysta z istniejącego wspólnego
  kontekstu weryfikacji. Natywnego PostgreSQL tutaj nie uruchamiano.
- Odczyt prywatnych pierwotnych warunków zakupu zachowuje osobny, spójny
  snapshot SQLite z odświeżeniem sesji, bez rezerwowania blokady zapisu.
- Lista aktywnych adresów dostawcy w SQLite sprawdza teraz sesję w tym samym
  snapshotcie co dane dostawy. Trzy dodatkowe próby cofnięcia sesji, wygaśnięcia
  i zmiany roli odtworzyły problem przed poprawką; po zmianie nie zwracają adresu.
  Ścieżka PostgreSQL tego odczytu pozostaje bez zmian.
- Uaktualniono trzy starsze testy struktury kodu i makiet: rozpoczęcie
  transakcji jest teraz sprawdzane we wspólnym kontekście.

SQLite nadal szereguje zapisujących. Operacja, która uzyskała blokadę i została
uprawniona przed wylogowaniem, może zakończyć się przed nim. Nie obiecujemy
anulowania już zakończonych operacji ani usunięcia wcześniej wyświetlonych danych.
Nie zmieniano magazynu, kluczy, zapisanych zakupów ani schematu istniejącej bazy.

## Potwierdzone kontrole

- Paczka transakcyjna: **61 PASS, 0 FAIL, 0 SKIP** w siedmiu modułach.
  Obejmuje 45 nowych przypadków: początkowe 43 oraz kontrolę kolejności SQL
  i kontrolę obejmowania mutacji wspólną granicą autoryzacji.
- Paczka po dodaniu ochrony adresów: **60 PASS, 0 FAIL, 0 SKIP** w czterech
  modułach. Nowy moduł zawiera łącznie 48 przypadków.
- Sześć starszych modułów księgowych wywoływało chronione funkcje bez tokenu.
  Testy dostały prawdziwe sesje syntetycznych użytkowników; dwa przypadki
  podszywające rolę rolnika kontem klienta zastąpiono osobnymi kontami rolników.
  Zachowano kontrolę własności i odmowy 404. Paczka: **8 PASS, 0 FAIL**.
  Nie zmieniano aplikacji w celu dopuszczenia zapisu bez sesji.
- Sprawdzenie odrzuconych operacji porównuje hash całej testowej bazy przed
  i po próbie. Cofnięcie sesji jest zachowane, operacja biznesowa nie zmienia danych.
- Istniejące testy sesji przez rzeczywisty TCP HTTP i restarty: PASS.
- Pakiet rzeczywistej akceptacji HTTP: **4/4 zadania PASS**, raport kompletny,
  `sources_unchanged: true`. Zakup, koszyk wielu rolników, dostawa, pełny zwrot,
  prywatność i opłata raz na przesyłkę pozostają objęte kontrolą.
- `git diff --check`: PASS.

Wcześniejsze pełne przebiegi z tej kontynuacji nie są końcowym dowodem:
zakres rozszerzono podczas pracy, co unieważniło źródła jednego przebiegu,
a kolejny ujawnił wymagające uzupełnienia sesji dane testowe księgowości.
Końcowy raport powstaje z nowej pełnej regresji po wszystkich zmianach.
Nie sumujemy powtórzeń, zadań HTTP i kontroli SQL z liczbą przypadków pytest.

## Pełna regresja końcowa

**3472 PASS, 0 FAIL, 17 SKIP — 3489 przypadków,
277/277 modułów.** Raport kompletny, `success: true`, `sources_unchanged: true`.
Odcisk przetestowanych źródeł: `d9707d0d45a9f12b55685ddfc52291ad180dc16f2458cd130b818afd40780ec9`.
Pełny przebieg wykonano od początku po wszystkich zmianach kodu i danych testowych.
Zestawienie bez lokalnych ścieżek i surowych logów:
[`audits/regression_2026-10-17_v3_summary.json`](audits/regression_2026-10-17_v3_summary.json).

Pominięte przypadki (nie są zaliczeniami):

- `test_mobile_offline.py`: 1 SKIP.
- `test_postgres_environment.py`: 2 SKIP.
- `test_postgres_full_api_optin.py`: 11 SKIP.
- `test_postgres_transaction_integration_optional.py`: 2 SKIP.
- `test_roles_offline.py`: 1 SKIP.

## Zakres i pozostałe bramy

Wersja demonstracyjna, nadal bez gotowości produkcyjnej. Natywny Windows,
PostgreSQL i Chromium pozostają niezweryfikowane w tym środowisku.
19 historycznych modułów lokalnych pozostaje poza repozytorium. Pozostają
przegląd RLS, pełna ocena bezpieczeństwa i praw konsumenta, procesy odzyskiwania
konta/PIN-u oraz sprawdzone procedury kopii i odtwarzania.

Nie zmieniono kwot w całkowitych groszach, opłaty raz na przesyłkę, odbioru
PIN-em, pełnego zwrotu przy winie dostawcy ani prywatności telefonów.
Płatności są symulowane. Nie zmieniano `main`, domeny, hostingu ani produkcji.
Zapis GitHub pozostaje niepotwierdzony po wcześniejszym błędzie 403; lokalne
commity są przekazywane w zbiorczej paczce z instrukcją bezpiecznego łączenia.
