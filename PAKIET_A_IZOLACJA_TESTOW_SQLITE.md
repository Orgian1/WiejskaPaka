# Pakiet A — powtarzalne, odizolowane testy

Problem: uruchamianie całego zestawu pytest z istniejącym plikiem SQLite
może powodować błędy wynikające z danych pozostałych po wcześniejszym teście.

## Bezpieczne uruchomienie

```bash
python scripts/run_tests_isolated.py -q
```

Skrypt tworzy osobny tymczasowy katalog i nową bazę SQLite dla **całego
uruchomienia**; po zakończeniu usuwa plik. Usuwa z otoczenia procesu potomnego
`DATABASE_URL`, `WP_TEST_POSTGRES_DSN`, `WP_TEST_DATABASE_URL` i flagę zdalnej
bazy testowej. Nie modyfikuje istniejącej bazy Neon, hostingu ani płatności.

Uwaga: baza jest nowa **na przebieg**, nie na pojedynczy test. Testy współdzielą
ją w ramach jednego uruchomienia; pełna izolacja per-test wymaga dalszych prac.
Rzeczywiste testy PostgreSQL trzeba wykonywać oddzielnie, na wyraźnie
wydzielonej testowej instancji.
