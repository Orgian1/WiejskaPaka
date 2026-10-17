# Kontynuacja paczki B/10921–B/11280

- Dodano `scripts/run_isolated_pytest.py`, uruchamiający moduły pytest w oddzielnych procesach i zapisujący wyniki JSON.
- Pełna regresja `pytest -x` wykazała błąd `tests/test_api.py::test_flow`: HTTP 409 zamiast 201 przy rejestracji; uruchomienie samego pliku `tests/test_api.py` przeszło 2/2. Wskazuje to na możliwy konflikt stanu pomiędzy modułami testów; przyczyna nie została jeszcze potwierdzona.
- Uruchomiono pierwszych 10 modułów osobno, wyniki w `RAPORT_B_10921_11280_IZOLACJA_10.json`.
- GitHub: nie wysłano kodu, ponieważ nie ustalono docelowego repozytorium ani jego prywatności. Nie uruchamiano GitHub Actions ani płatnych usług.
- Pełna regresja, PostgreSQL, Chromium, urządzenia fizyczne i końcowy audyt pozostają otwarte.
