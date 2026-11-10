# WiejskaPaka — historia symulowanych płatności, 17.10.2026

Punkt wyjścia: `ebf2a9554ff9460bc7f79c51e96c8b3b23145ff1`.
Gałąź lokalna: `wiejskapaka-import`. Siódma zbiorcza paczka napraw.
Na polecenie użytkownika pracowano bez prób połączenia z GitHubem.

## Odtworzony problem

Same kwoty i stan symulacji mogły wyglądać prawidłowo, mimo że zdarzenia
płatności były usunięte albo sprzeczne. Ponowienie zwrotu mogło wtedy zwrócić
potwierdzenie sukcesu. Zapis kolejnego zdarzenia także nie zawsze sprawdzał,
czy dotychczasowa historia wyjaśnia bieżący zapis.

Nowy zestaw przed poprawką: **13 FAIL, 2 PASS — 15 przypadków**.
To osobne próby celowo uszkodzonych danych syntetycznych, nie odtworzenie
historycznych 37 błędów Windows ani dowód uszkodzenia rzeczywistych zakupów.

## Zmiana

Kontrola odtwarza legalne przejścia obecnego, acyklicznego automatu symulacji
od stanu oczekiwania na płatność. Każde zdarzenie musi pasować do jedynej
dozwolonej kolejności przejść, mieć zgodny `state_after` i doprowadzić do
zapisanych kwot, stanu oraz zbioru identyfikatorów zdarzeń.

Kolejność wynika z automatu, nie z sortowania dat lub identyfikatorów. Równe
znaczniki czasu i cofnięcie zegara nie unieważniają spójnej historii.
Kontrola nie certyfikuje poprawności dat. Obecny automat dopuszcza najwyżej
trzy przejścia; dłuższa historia jest odrzucana. Rozbudowa automatu wymaga
również aktualizacji tego ograniczenia i testów.

Sprawdzenie działa przed zwrotem, potwierdzeniem jego ponowienia i zapisem
kolejnego zdarzenia. Przed zapisem porównywany jest także przekazany snapshot
z aktualną symulacją w bazie. Nieaktualny snapshot nie może zwrócić starego
wyniku ponowienia ani nadpisać nowszego stanu.

Brakujące lub sprzeczne zdarzenia skutkują odmową 409 w API. Nie są dopisywane
automatycznie. Nie zmieniano schematu, kluczy ani istniejących zakupów.
Historyczna symulacja bez wymaganych zdarzeń będzie wymagać wyjaśnienia,
a nie automatycznego uznania płatności lub zwrotu.

## Potwierdzone kontrole

- Paczka regresji: **55 PASS, 0 FAIL, 0 SKIP** w pięciu modułach.
- Nowy moduł obejmuje usunięcie płatności lub zwrotu z historii, nieprawidłowy
  stan po zdarzeniu, nieznany typ i powtórzone przejście. Sprawdza zakup
  pojedynczy i przesyłkę, pierwszy zwrot i ponowienie oraz ponowienie zdarzenia.
- Każda odrzucona operacja porównuje hash danych tabel testowej bazy przed
  i po żądaniu. Sprzeczny zapis pozostaje bez zmian do analizy.
- Dwie dodatnie próby zachowują poprawny zwrot przy równych i odwróconych
  datach zdarzeń, bez zwiększenia kwoty i bez zmian w bazie przy ponowieniu.
- Istniejące testy sprawdzają legalny cykl płatność–odbiór–wypłata, pełny
  zwrot, powtórzenia oraz odrzucenie nieaktualnego snapshotu i rywalizację
  rzeczywistych zapisujących w SQLite.

Nowe próby używają ASGI TestClient i danych syntetycznych. Środowisko izoluje
moduły w osobnych procesach, używa jednorazowych SQLite i nie przekazuje
produkcyjnych sekretów ani adresów baz. Wszystkie płatności są symulowane.

## Pełna regresja końcowa

**3537 PASS, 0 FAIL, 17 SKIP — 3554 przypadki, 281/281 modułów.**
Raport kompletny, `success: true`, `sources_unchanged: true`.
Przebieg wykonano od początku po ostatniej zmianie kodu i testów, bez wznowienia.
Odcisk źródeł: `bc0fa3e02a5448b4dc4ef8a3a36170deb33cb8c715345fe646e656e1ad43cc54`.

Osobna akceptacja rzeczywistego TCP HTTP: **4/4 zadania PASS**, także bez zmiany
źródeł. Obejmuje zakup, dostawę, pełny zwrot, koszyk wielu rolników, prywatność
oraz pojedynczą opłatę za przesyłkę. Nie sumujemy jej z przypadkami pytest.
Zestawienie bez surowych logów i lokalnych ścieżek:
[`audits/regression_2026-10-17_v7_summary.json`](audits/regression_2026-10-17_v7_summary.json).

Pominięcia: PostgreSQL 15 przypadków, mobilny test offline 1 i rozszerzony test
ról offline 1. Nie są zaliczeniami. Przyrost względem v6 wynika z 15 nowych
przypadków; nie oznacza wykonania historycznych lokalnych modułów Windows.
`git diff --check`: PASS.

## Pozostałe ograniczenia

Spójny komplet sfałszowanych danych nie jest wykrywany kryptograficznie.
Nie dodano podpisów dziennika, niezależnego rejestru ani narzędzia naprawy
księgowej. Nie rozszerzano w tej paczce wszystkich raportów odczytowych o nową
kontrolę historii. To ochrona opisanych zapisów i potwierdzeń, nie pełny audyt.
Dalszej kontroli wymaga powiązanie przyczyny zwrotu z historią zamówienia;
spójność samego automatu płatności nie dowodzi poprawności wszystkich decyzji
biznesowych ani autentyczności zdarzeń.

Natywny Windows, PostgreSQL i Chromium nadal wymagają weryfikacji.
19 historycznych modułów lokalnych pozostaje poza repozytorium i nie zostało
tu uruchomionych. Nadal potrzebne są pełny audyt bezpieczeństwa i RLS,
weryfikacja zgodności konsumenckiej, wydajności, kopii i odtwarzania.
Aplikacja nie jest gotowa do wdrożenia produkcyjnego.

Zachowano całkowite grosze, opłatę raz na przesyłkę, PIN, pełny zwrot przy winie
dostawcy i prywatność telefonów. Nie podłączano domeny, hostingu ani rzeczywistych
płatności. `main` pozostaje bez zmian. Poprawki zapisano lokalnie; w tej
kontynuacji nie wykonywano odczytów ani zapisów zdalnego GitHub.
