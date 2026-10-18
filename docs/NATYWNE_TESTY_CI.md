# Natywne bramy CI

Workflow `.github/workflows/native-tests.yml` działa po aktualizacji
`wiejskapaka-import` oraz gałęzi `preview/**`. Każda gałąź ma osobną grupę
przebiegów, więc jej testy nie przerywają testów innej gałęzi. Nie wdraża aplikacji i nie zmienia `main`.
Każda brama korzysta z osobnej maszyny GitHub-hosted:

- Windows: osobne szybkie zadanie `windows_recovery` uruchamia 80 przypadków
  kopii/odtwarzania, resetu hasła, przeglądu profilu rolnika, nowego demo
  i interfejsu rozliczeń; publikuje własny
  raport. Jego powodzenie jest warunkiem startu pełnego zadania `windows`.
  Pełne zadanie powtarza najpierw 80 przypadków kopii/odtwarzania i resetu hasła, następnie
  pełna regresja; Python 3.12, Node 24 i `requirements-lock.txt`.
  Pierwszy zestaw jest powtarzanym podzbiorem pełnego, nie dodatkowymi
  unikalnymi przypadkami. Jego błąd zatrzymuje bramę przed długą regresją.
  Wykonanie na innym systemie jest odrzucane. Opcjonalne testy natywne są
  pomijane w tej bramie i wykonywane w osobnych zadaniach.
- PostgreSQL: jednorazowy kontener PostgreSQL 16 i 18 przypadków adaptera,
  transakcji, migracji, ograniczonej roli aplikacji i rzeczywistego HTTP,
  w tym prywatnych zgłoszeń problemów z zakupem.
  Dozwolony jest tylko DSN loopback z nazwą testową.
- Chromium: 8 widoków wszystkich ról z rzeczywistym HTTP i danymi demo
  (320 i 1280 px), 2 pełne scenariusze odbioru/dostawy/przeglądu profilu, wcześniejsze 7 przypadków offline, w tym cztery role, oraz
  2 przypadki kolejki administratora (320 i 1280 px),
  2 przypadki zasad sprzedawcy (320 i 1280 px), 2 przypadki resetu hasła przez rzeczywisty HTTP (390 i 1280 px),
  2 scenariusze zgłoszeń problemów klient–rolnik–administrator (320 i 1280 px),
  2 scenariusze stron katalogu i koszyka przy 52 ofertach (320 i 1280 px),
  a także kontrola HTTP przy pięciu rozmiarach okna. SKIP lub brak przeglądarki nie jest sukcesem.

Hasło `disposable-ci-only` jest jawnym hasłem wyłącznie jednorazowego kontenera,
bez produkcyjnych danych. Testy nie używają Neon ani sekretów repozytorium.
Fixture usuwa tylko losowe zasoby utworzone przez siebie w tym kontenerze.
Istniejące bazy użytkownika nie są podłączane.

Uprawnienia zadania to tylko `contents: read`; checkout nie zachowuje
poświadczeń. Procesy dostają listę dozwolonych zmiennych systemowych,
testowy SQLite i, tylko w bramie PostgreSQL, zweryfikowany DSN testowy.
Inne sekrety, produkcyjne adresy i klucze nie są przekazywane.

Akcje przypięto do SHA oficjalnych wydań: checkout v7.0.1, setup-python v7.0.0,
setup-node v7.1.0 i upload-artifact v7.0.2. Pełne SHA znajdują się w workflow.

## Dowody wykonania

`python -m scripts.run_native_ci <windows-recovery|windows|postgres|browser> --report wynik.json`
zapisuje odciski kodu, workflow, zależności, testów i helperów oraz liczniki
i kody zakończenia. Błędy pełnej regresji dodatkowo podają wyłącznie nazwy
modułów należących do repozytorium, bez zawartości `output_tail`. Gdy pełne
liczniki są niedostępne, raport jest odrzucany, a nazwy niekompletnych modułów
i modułów z przekroczonym czasem pozostają w oczyszczonej diagnostyce.
Brak liczników nie jest zerem wykonanych testów i nie oznacza zaliczenia.
Surowe stdout/stderr, XML, zmienne środowiska, ścieżki
tymczasowe, klucze i dane testowe nie są publikowane jako artefakty.
Podsumowania mają retencję 7 dni. Logi procesów testowych są przechwytywane
i odrzucane; runner wypisuje tylko PASS albo FAIL.

Natywne bramy wymagają minimum 18 przypadków PostgreSQL, 36 w bramie Chromium
(27 wcześniejszych oraz 9 prywatnego podglądu POSIX)
i 80 przypadków wstępnego testu Windows,
bez błędów i pominięć. Windows wymaga kompletnego raportu regresji. Zmiana
źródeł lub helperów podczas wykonania unieważnia wynik. Błąd instalacji,
brak wyniku, timeout, SKIP i anulowanie nie są zaliczeniem.

Testy `test_native_ci_runner.py` używają makiet procesów; nie dowodzą wykonania
Windows, PostgreSQL ani Chromium. Sama konfiguracja również nie jest wynikiem.
Miarodajny jest zakończony przebieg Actions dla konkretnego commitu.

Brakujących historycznych modułów lokalnych nie dodawano do repozytorium.
Te bramy nie zastępują audytu bezpieczeństwa/RLS, zgodności konsumenckiej,
wydajności oraz kopii i odtwarzania. Nie oznaczają gotowości produkcyjnej.

Oficjalne źródła konfiguracji:
https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers
https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

Szybki raport Windows nie jest pełną regresją. Te same 80 przypadków
wykonuje się w osobnym zadaniu, na początku pełnego zadania i w pełnej
regresji; nie sumować ich jako nowych testów. Wynik etapu PASS/FAIL jest
wypisywany na bieżąco bez logów procesów i bez danych kont.
