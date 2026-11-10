# WiejskaPaka — naprawa regresji, 17 października 2026

## Zakres i pochodzenie kodu

Gałąź: `wiejskapaka-import`. Punkt wyjścia: `c5e1b49d337b8641eec2933321d750017b788168`.
Odcisk aplikacji na wejściu: `93f8883981afeb3ec604d4ce2fdc8610540c9bdcf0f642755f07d7a474f35647` — taki sam jak w raporcie użytkownika.
Repozytorium zawiera 274 moduły `tests/test_*.py`, a lokalny raport użytkownika 293.
Różnica 19 wynika z istniejących wykluczeń w `.gitignore`; ta poprawka nie usuwa testów.
Nie jest to ponowne wykonanie dokładnie tych samych 3591 przypadków z Windows.
W szczególności nie ma w klonie `test_b11303_preflight_secret_redaction.py`
ani `test_checkout_vault_ui_cli.py`; ich wynik pozostaje niezweryfikowany.

## Poprawki

| Obszar | Przyczyna i zmiana | Granica dowodu |
| --- | --- | --- |
| Start PostgreSQL | Test atomiczności dziedziczył `WIEJSKAPAKA_DB` od runnera. Test usuwa sprzeczne ustawienie przed zamockowaną próbą PostgreSQL. Produkcyjny zakaz mieszania baz pozostaje. | Błąd odtworzony na Linux, oba przypadki przechodzą po poprawce. |
| Czysty klon | Test schematu importował wykluczony lokalny moduł. Zastąpiono import samodzielną syntetyczną konfiguracją, bez połączenia z bazą. | Błąd zbierania testów odtworzony i usunięty. |
| SQLite i Windows | Kontekst połączenia SQLite zarządza transakcją, ale nie zamyka pliku. Dodano jawne zamknięcie w audycie, skryptach akceptacji i testach restartu. | Linux PASS; rzeczywiste blokady plików na Windows wymagają powtórki. |
| Ścieżki SQLite | URI powstaje przez `Path.as_uri()`, poprawnie kodując znaki specjalne i ścieżki dysków. | Dodany przypadek ścieżki z polskimi znakami, `#` i `%` przechodzi. |
| Kodowanie diagnostyki | Procesy testowe dostają UTF-8, a runnery jawnie dekodują przechwycone wyjście jako UTF-8. Raporty HTTP są zapisywane w UTF-8. | Osobny eksperyment z rodzicem bez UTF-8 poprawnie zapisał polski komunikat celowo błędnego testu. |
| Hashowanie i ścieżki testowe | Syntetyczny plik w teście agregacji ma jawne LF; porównania ścieżek używają `Path`. Dodano `.gitattributes` dla stałych zakończeń linii. | Testy agregacji i runnerów przechodzą na Linux; Windows wymaga potwierdzenia. |
| Funkcje systemowe | Uprawnienia POSIX, synchronizacja katalogu i rotacja klucza nie są kontraktem Windows. Testy właściwe dla POSIX mają jawny warunek platformy; test składni shell wymaga `sh`; tworzenie symlinków wymaga uprawnień. | Pominięcie nie oznacza zaliczenia zabezpieczenia. Nie zmieniono implementacji ochrony kluczy. |
| Restart i rotacja na Windows | Testy HTTP nadal sprawdzają restart, ponowienie i retencję. Na Windows oczekują bezpiecznej odmowy rotacji, bez podmiany klucza. | Test bezpiecznej odmowy wykonano także na Linux przez podmianę wyłącznie informacji o platformie w module. Natywnego Windows nie uruchamiano. |

## Środowisko i metoda

Python 3.12.14, Node.js 24.19.0, Linux; osobny venv i dokładne wersje z
`requirements-lock.txt`. `pip check`: PASS. Każdy moduł pytest ma osobny proces
oraz nową tymczasową bazę SQLite. Proces nadrzędny uruchomiono z minimalnym
środowiskiem bez sekretów. Nie korzystano z produkcyjnego PostgreSQL, Neon,
kluczy użytkownika ani rzeczywistych płatności.

Pierwszy przebieg diagnostyczny miał niepełny wynik i brak Node w ograniczonym
PATH. Nie jest dowodem pełnej regresji. Node dodano do PATH końcowego przebiegu,
bez zmiany kodu testów JavaScript ani sztucznego ich pomijania.

## Potwierdzone paczki

- Paczka 1: 16 modułów, 85 przypadków: 84 PASS, 0 FAIL, 1 SKIP.
- Paczka 2: 9 modułów, 72 przypadki: 72 PASS, 0 FAIL, 0 SKIP.
- Paczek i powtórek nie sumuje się z pełną regresją.
- `git diff --check`: PASS. `pip check`: PASS.
- Brama `python -m scripts.release_gate`: kod 2, `production_ready: false`.
  Jest to oczekiwana blokada przy braku formalnie zarejestrowanych dowodów wszystkich bram.

## Pełna regresja końcowa

**3409 PASS, 0 FAIL, 17 SKIP — 3426 przypadków, 274/274 moduły.**
Raport kompletny: `complete: true`, `success: true`, `sources_unchanged: true`.
Odcisk przetestowanych źródeł: `c1e7cf34460740bc1b19030c75b357046379641a5ab919b9a456c9c214b78660`.
Zestawienie modułów, ich hashy i liczników bez lokalnych ścieżek i tracebacków:
[`audits/regression_2026-10-17_summary.json`](audits/regression_2026-10-17_summary.json).

Pominięcia w końcowym przebiegu:

- `test_mobile_offline.py`: 1 SKIP.
- `test_postgres_environment.py`: 2 SKIP.
- `test_postgres_full_api_optin.py`: 11 SKIP.
- `test_postgres_transaction_integration_optional.py`: 2 SKIP.
- `test_roles_offline.py`: 1 SKIP.

Pominięte przypadki wymagają zewnętrznych warunków, np. natywnego PostgreSQL lub przeglądarki. SKIP nie jest wynikiem PASS.

## Pozostałe prace i gotowość

Wersja pozostaje demonstracyjna. Nie jest gotowa do wdrożenia produkcyjnego.
Potrzebna jest pełna powtórka na Windows, w tym lokalne moduły wykluczone z repo.
Nie da się przypisać wszystkich 37 lokalnych błędów do przyczyn bez ich pełnych
tracebacków; wykryte zależności od platformy są wskazaniami do weryfikacji,
a nie deklaracją zaliczenia Windows.

Pozostają natywne testy PostgreSQL, ocena ochrony dostępu/RLS, rzeczywista
przeglądarka i urządzenia mobilne, przegląd bezpieczeństwa i praw konsumenta,
procedury odzyskiwania konta/PIN-u oraz operacyjne kopie i odtwarzanie danych.
Integracje płatności i infrastruktura produkcyjna pozostają przyszłym etapem.
Rotacja kluczy na Windows nadal jest celowo niedostępna; nie omijano tej blokady.

Nie zmieniono reguł kwot w groszach, opłaty raz na przesyłkę, odbioru PIN-em,
pełnego zwrotu przy winie dostawcy, prywatności telefonów ani praw konsumenta.
Nie zmieniono `main`, baz i kluczy użytkownika, domeny ani hostingu.

## Odtworzenie

Z katalogu projektu, po instalacji `requirements-lock.txt` w osobnym venv:

```powershell
.\.venv\Scripts\python.exe scripts/run_tests_per_file.py --report moj_raport_po_naprawie.json
.\.venv\Scripts\python.exe scripts/analyze_regression_report.py --help
```

Do testów JavaScript potrzebny jest Node.js w PATH. Pominięte funkcje platformy
oraz testy wymagające jawnej konfiguracji nie są dowodem ich gotowości.
Nie kopiować do repo lokalnych baz, kluczy, konfiguracji środowiska ani surowych
raportów zawierających lokalne ścieżki lub potencjalne dane w tracebackach.

## Zapis zmian

Zapis do GitHub był zablokowany: Git CLI nie ma poświadczeń, a połączona
integracja odrzuciła utworzenie drzewa commitu błędem 403
`Resource not accessible by integration`. Zdalna gałąź nie została zmieniona.
Poprawki zapisano lokalnie na `wiejskapaka-import` i dołączono jako bundle Git
oraz patch w paczce przekazania. Nie wykonywano force push ani zmian `main`.
