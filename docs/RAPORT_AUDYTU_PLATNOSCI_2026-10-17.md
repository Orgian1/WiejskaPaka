# WiejskaPaka — diagnostyka historii płatności, 17.10.2026

Punkt wyjścia: `eea0c09548682167874f256b3544deb8a6b6a0c7`.
Gałąź lokalna: `wiejskapaka-import`. Dziewiąta zbiorcza paczka napraw.
Prace wykonano bez prób połączenia z GitHubem.

## Odtworzone problemy

Audyt kwot mógł zwrócić `ok: true` mimo nieznanego stanu płatności, brakujących
lub sprzecznych zdarzeń albo niezgodnego wpisu zamknięcia zamówienia. Ochrona
zapisu odrzucała już takie dane, ale diagnostyka nie pokazywała przyczyny.

Narzędzie lokalnego audytu składało URI SQLite bez kodowania ścieżki.
Znaki `#` i `%` w nazwie mogły zmienić interpretację ścieżki, a zgubiony parametr
trybu odczytu mógł spowodować otwarcie innego pliku. Nieprawidłowy schemat
kończył się tracebackiem zamiast kontrolowanego komunikatu.

Nowe próby na czystym v8: **9 FAIL, 3 PASS — 12 przypadków**.
Odtworzenie wykonano w osobnej lokalnej kopii bazowego commitu z tym samym
finalnym nowym modułem testowym. Są to syntetyczne przypadki, niezależne
od historycznych 37 błędów Windows. Nie dotykano produkcyjnych baz ani sekretów.

Wcześniejszy próbny przebieg zawierał dodatkowy błąd narzędzia testowego:
pytest zebrał importowaną funkcję pomocniczą jako test. Import nazwano aliasem,
powtórzono porównanie przed/po i nie zaliczano tego błędu do usterek aplikacji.

## Zmiana

Audyt zachowuje istniejące kontrole kwot i dodaje trzy kody:

- `INVALID_PAYMENT_STATE`: stan symulacji lub jego kwoty są niespójne.
- `PAYMENT_HISTORY_MISMATCH`: zdarzenia nie wyjaśniają zapisanego stanu i kwot.
- `REFUND_CONTEXT_MISMATCH`: zwrot nie zgadza się z zamknięciem zamówienia.

Wykorzystuje te same walidatory historii i kontekstu co ścieżki zapisu.
Raport zawiera wyłącznie kod i identyfikator zamówienia, bez danych osób,
identyfikatorów zdarzeń, haseł, PIN-ów i treści SQL. Nie naprawia danych.

CLI używa URI z `Path.as_uri()` i `mode=ro`, rozpoczyna spójny snapshot odczytu
przez `BEGIN` oraz jawnie zamyka połączenie. Audytor wywoływany bezpośrednio
przyjmuje od wywołującego transakcję zapewniającą spójny odczyt; sam nie
zatwierdza ani nie wycofuje cudzej transakcji.

Kod zakończenia CLI: 0 dla poprawnego audytu, 1 dla wykrytych niespójności,
2 dla niedostępnego audytu lub niepoprawnych argumentów. Błąd SQLite daje
ogólny JSON `AUDIT_UNAVAILABLE` z `complete: false`, bez tracebacka i ścieżki.
Brakujący plik nie jest tworzony. Audyt wymaga aktualnego schematu aplikacji;
nie migruje starszej bazy ani nie zgaduje brakujących dowodów.

Przykład dla wyłącznie lokalnej, testowej kopii danych:

```powershell
python -m scripts.audit_test_payments --sqlite "C:\Testy-WiejskaPaka\kopia.sqlite"
```

## Potwierdzone kontrole

- Paczka regresji: **54 PASS, 0 FAIL, 0 SKIP** w czterech modułach.
- Nowe 12 przypadków obejmuje stan, historię, przyczynę zwrotu, brak autora
  i zamknięcia, duplikat zamknięcia oraz rzeczywisty proces CLI.
- Audyt działa z `PRAGMA query_only=ON` wewnątrz transakcji. Hash danych tabel
  przed i po jest identyczny; raporty problemów mają tylko `order_id` i `code`.
- CLI sprawdzono dla zwykłej nazwy i nazwy ze spacją, `#` i `%`, poprawnych
  także jako nazwy Windows. Plik i lista plików po audycie pozostają bez zmian.
- Próby niepoprawnego schematu i brakującego pliku potwierdzają kontrolowaną
  odmowę bez tworzenia bazy ani ujawnienia ścieżki w błędzie SQLite.
- Pięć starszych prób finansowych zachowano. Ich pozytywną bazę testową
  uzupełniono o rzeczywistą sekwencję płatność–zwrot oraz wpis zamknięcia,
  zamiast wpisywać sam stan końcowy bez wymaganej historii. Negatywne kontrole
  kwot, zwrotu z wypłatą i osieroconego zdarzenia nadal są wykonywane.

Testy używają jednorazowych SQLite i syntetycznych kont. Proces CLI dostaje
tylko niezbędne zmienne systemowe i konfigurację testową. Płatności są symulowane.

## Pełna regresja końcowa

**3573 PASS, 0 FAIL, 17 SKIP — 3590 przypadków, 283/283 moduły.**
Raport kompletny, `success: true`, `sources_unchanged: true`.
Przebieg wykonano od początku po ostatniej zmianie kodu i testów, bez wznowienia.
Odcisk źródeł: `5c096cf721fa3678913c19d4818de6215f66d64c9e9f5f440c8d93c74f4b3102`.

Osobna akceptacja rzeczywistego TCP HTTP: **4/4 zadania PASS**, także bez zmiany
źródeł. Obejmuje zakup, dostawę, pełny zwrot, koszyk wielu rolników, prywatność
oraz pojedynczą opłatę za przesyłkę. Nie sumujemy jej z przypadkami pytest.
Zestawienie bez surowych logów i lokalnych ścieżek:
[`audits/regression_2026-10-17_v9_summary.json`](audits/regression_2026-10-17_v9_summary.json).

Pominięcia: PostgreSQL 15 przypadków, mobilny test offline 1 i rozszerzony test
ról offline 1. Nie są zaliczeniami. Przyrost względem v8 wynika z 12 nowych
przypadków; nie oznacza wykonania historycznych lokalnych modułów Windows.
Zbliżona liczba przypadków do pierwotnego raportu użytkownika nie oznacza
identycznego zestawu testowego. `git diff --check`: PASS.

## Pozostałe ograniczenia

Kontrole nie są kryptograficznym dowodem autentyczności spójnie sfałszowanych
danych ani pełnym audytem księgowym. Nie zmieniano pozostałych raportów
miesięcznych, uzgadniania z operatorem czy planów wypłat. Dla bezpośredniego
wywołania audytora zapewnienie snapshotu należy do wywołującego. Test nie
potwierdza wszystkich zachowań plików pomocniczych SQLite w trybie WAL.

Natywny Windows, PostgreSQL i Chromium nadal wymagają weryfikacji.
19 historycznych lokalnych modułów pozostaje poza repozytorium. Nadal potrzebne
są pełny audyt bezpieczeństwa i RLS, weryfikacja zgodności konsumenckiej,
wydajności oraz procedur kopii i odtwarzania. Aplikacja nie jest gotowa do produkcji.

Nie zmieniono zasad groszy, pojedynczej opłaty za przesyłkę, PIN-u, pełnego
zwrotu przy winie dostawcy ani prywatności telefonów. Nie podłączano domeny,
hostingu i rzeczywistych płatności. `main` pozostaje bez zmian. Nie wykonywano
odczytów ani zapisów zdalnego GitHub; poprawki są lokalne.
