# WiejskaPaka — B/6241–B/6600 — duża paczka weryfikacji lokalnej

## Zakres

Dodano `scripts/run_large_local_gate.py`: duża bramka akceptacyjna, która łączy istniejące scenariusze prawdziwego HTTP, kontrolę uprawnień ról, osiem izolowanych modułów regresyjnych, kontrolę składni JS i kompilację Python. Wyniki zapisuje do `RAPORT_DUZA_PACZKA_LOKALNA.json` i pozwala wznowić pozytywnie zakończone etapy.

## Ważna poprawka metodologii

Pierwsza próba uruchomienia ośmiu modułów pytest we wspólnym procesie spowodowała dwa błędy z powodu współdzielonej bazy testowej. Nie były to dowody awarii systemu w izolowanych testach. Zmieniono bramkę, aby każdy moduł pytest uruchamiać w osobnym procesie. Wszystkie osiem modułów przeszło następnie pozytywnie. Zapis wcześniejszego nieudanego uruchomienia nie jest przechowywany w finalnym raporcie; szczegóły opisano tutaj.

## Wyniki

Finalny raport `RAPORT_DUZA_PACZKA_LOKALNA.json` zawiera 12/12 pozytywnych etapów (4 HTTP i kontrola uprawnień liczone jako dwa etapy, 8 izolowanych modułów, JS i Python). Zestaw HTTP zawiera 95 kontroli według wcześniejszej konfiguracji. Wyniki nie stanowią testów PostgreSQL ani testów na fizycznych telefonach.

## Granice bezpieczeństwa

Brama usuwa zmienne środowiskowe związane z połączeniem do zewnętrznej bazy, nie uruchamia produkcyjnych płatności ani nie dotyka Neon. Testy HTTP korzystają z jednorazowych baz SQLite. Nadal wymagane: PostgreSQL na odizolowanym serwerze, pełna sesja Chromium przez HTTP, testy na telefonach, audyt prawny i bezpieczeństwa.

Uruchomienie: `python scripts/run_large_local_gate.py`.
