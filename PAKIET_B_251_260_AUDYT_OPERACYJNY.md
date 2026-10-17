# B/251–B/260 — audyt operacyjny SQLite (pakiet roboczy)

Dodano `scripts/run_order_audit.py`: uruchamiany ręcznie audyt zamówień w istniejącej bazie SQLite, otwieranej w trybie tylko do odczytu. Raport JSON zawiera liczbę sprawdzonych zamówień i produktów oraz kody problemów bez danych osobowych. Opcjonalny zapis raportu jest atomowy (plik tymczasowy i os.replace). Kody zakończenia: 0 bez błędów, 1 niespójności, 2 błąd wykonania.

Przykład: `python scripts/run_order_audit.py --database /sciezka/do/test.sqlite3 --report /sciezka/do/audyt.json`

Testy: `python -m unittest discover -s tests -p 'test_order_audit_cli_b251.py' -q` (6), `python -m unittest discover -s tests -p 'test_order_integrity_b241.py' -q` (9). Wszystkie 15 przeszły lokalnie. Nie testowano Neon/PostgreSQL ani całej aplikacji. Numeracja to zakres pakietu, a nie liczba niezależnych funkcji.
