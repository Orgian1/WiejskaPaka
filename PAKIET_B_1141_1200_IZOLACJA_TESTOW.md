# WiejskaPaka B/1141–B/1200 — izolacja testów

Zrealizowano nowy runner `scripts/run_tests_per_file.py`. Każdy plik testowy uruchamia się w osobnym procesie i osobnej tymczasowej bazie SQLite, aby uniknąć kolizji danych, zmiennych środowiskowych i importów modułów. Runner usuwa poświadczenia PostgreSQL/Neon z procesów potomnych, ogranicza wskazywane pliki do katalogu `tests/`, zapisuje raport JSON atomowo i nie dotyka bazy produkcyjnej.

Użycie: `python scripts/run_tests_per_file.py` (wszystkie moduły) lub `python scripts/run_tests_per_file.py test_b1081_line_integrity.py test_b741_admin_shipments.py`.

Weryfikacja: 2 nowe testy runnera przeszły; 3 wskazane moduły regresyjne przeszły oddzielnie. Pełna regresja całego repozytorium nie została wykonana. Nie zmieniano konfiguracji Neon, integracji płatności ani logiki kosztów dostawy.

Numeracja B/1141–B/1200 jest etykietą zakresu prac, nie liczbą ukończonych funkcji.
