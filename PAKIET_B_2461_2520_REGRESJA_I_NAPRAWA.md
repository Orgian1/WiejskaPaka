# WiejskaPaka B/2461–B/2520 — regresja i naprawa uruchamiania testów

## Wykonane
- Uruchomiono trzecią i czwartą grupę regresji: obie PASS (po 12 modułów).
- W piątej grupie wykryto dwa rzeczywiste błędy w testach mechanizmu regresji: skrypt odrzucał testy tworzone w katalogu tymczasowym pytest.
- Naprawiono walidację `selected` w `scripts/run_regression_chunks.py`: dopuszcza regularne pliki `test_*.py` wskazane jawnie także poza katalogiem projektu, ale odrzuca dowiązania symboliczne.
- Naprawiono generowanie manifestu SHA-256 dla jawnie wybranych plików spoza katalogu projektu.
- Ponownie uruchomiono testy `test_b96_b100_regression_runner.py` i `test_b2401_regression_per_file_isolation.py`: 6 PASS.
- Ponowne uruchomienie piątej grupy regresji rozpoczęto, ale zostało przerwane limitem czasu wykonania; częściowy raport jest zapisany w `regression_batch5_2461.json`.

## Ograniczenia
Nie ukończono pełnej regresji; PostgreSQL i testy przeglądarkowe pozostają niewykonane. Nie podłączono płatności produkcyjnych, hostingu ani domeny. Nie zmieniano konfiguracji Neon.
