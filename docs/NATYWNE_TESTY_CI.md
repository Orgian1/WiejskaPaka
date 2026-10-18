# Natywne bramy CI

Workflow `.github/workflows/native-tests.yml` działa po aktualizacji
`wiejskapaka-import`. Nie wdraża aplikacji i nie zmienia `main`.
Każda brama korzysta z osobnej maszyny GitHub-hosted:

- Windows: najpierw 23 przypadki kopii/odtwarzania i resetu hasła, następnie
  pełna regresja; Python 3.12, Node 24 i `requirements-lock.txt`.
  Pierwszy zestaw jest powtarzanym podzbiorem pełnego, nie dodatkowymi
  unikalnymi przypadkami. Jego błąd zatrzymuje bramę przed długą regresją.
  Wykonanie na innym systemie jest odrzucane. Opcjonalne testy natywne są
  pomijane w tej bramie i wykonywane w osobnych zadaniach.
- PostgreSQL: jednorazowy kontener PostgreSQL 16 i 15 przypadków adaptera,
  transakcji, migracji, ograniczonej roli aplikacji i rzeczywistego HTTP.
  Dozwolony jest tylko DSN loopback z nazwą testową.
- Chromium: wcześniejsze 7 przypadków offline, w tym cztery role, oraz
  2 nowe przypadki resetu hasła przez rzeczywisty HTTP (390 i 1280 px),
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

`python -m scripts.run_native_ci <windows|postgres|browser> --report wynik.json`
zapisuje odciski kodu, workflow, zależności, testów i helperów oraz liczniki
i kody zakończenia. Błędy pełnej regresji dodatkowo podają wyłącznie nazwy
modułów należących do repozytorium, bez zawartości `output_tail`. Surowe stdout/stderr, XML, zmienne środowiska, ścieżki
tymczasowe, klucze i dane testowe nie są publikowane jako artefakty.
Podsumowania mają retencję 7 dni. Logi procesów testowych są przechwytywane
i odrzucane; runner wypisuje tylko PASS albo FAIL.

Natywne bramy wymagają minimum 15 przypadków PostgreSQL, 9 przeglądarkowych
i 23 przypadków wstępnego testu Windows,
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
