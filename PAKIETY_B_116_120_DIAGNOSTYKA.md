# Pakiety B/116–B/120 — diagnostyka regresji

Wprowadzono pięć testów diagnostycznych: raport błędu pojedynczego pliku, przekroczenie limitu, odróżnienie częściowego przebiegu, poprawne oznaczenie pełnego przebiegu oraz kontynuację po błędzie.

Narzędzie `scripts/run_regression_chunks.py` zachowuje teraz fragment stdout testu po przekroczeniu limitu, zamiast samego wyjątku. Raport `complete` pozostaje `false` dla przebiegu częściowego. Kod zakończenia 0 dla wybranej partii oznacza wyłącznie powodzenie tej partii.

Testy celowane: 16 zaliczonych (`tests/test_regression_diagnostics_b116_b120.py`, `tests/test_regression_runner_b101_b105.py`, `tests/test_stabilization_02.py`). Osobny przebieg `tests/test_stabilization_02.py` + `tests/test_session_expiry_b86_b90.py`: 11 zaliczonych. Pełna regresja uruchomiona, lecz nie zakończyła się w limicie środowiska; NIE potwierdzono jej zaliczenia.

Nie wykonano żadnych zmian w Neon, RLS ani produkcyjnych płatnościach.
