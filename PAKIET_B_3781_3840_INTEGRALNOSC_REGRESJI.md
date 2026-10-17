# WiejskaPaka B/3781–B/3840 — integralność wznawianej regresji

- Naprawiono lukę w `scripts/run_regression_chunks.py`: wcześniej wznowienie sprawdzało tylko sumy plików testów, a nie aktualność kodu aplikacji.
- Raport grup testowych zapisuje teraz `application_sha256` i odrzuca wznowienie, jeśli zmieniły się źródła backendu, web, bazy lub skryptów.
- Wspólny algorytm odcisku źródeł dla nowego kontrolera znajduje się w `scripts/regression_manifest.py` (bez zależności cyklicznych).
- Dodano 2 testy sprawdzające odrzucenie nieaktualnego raportu i bezpieczne wznowienie bez zmian.
- Poprawiono 4 nieaktualne przypadki testowe w `test_b2341_resume_regression.py`, które tworzyły sztuczny raport bez odcisku aplikacji.

## Wyniki faktycznie wykonane

`python -m pytest -q tests/test_b3781_chunk_resume_source_integrity.py tests/test_b3721_regression_cache_integrity.py tests/test_b2401_regression_per_file_isolation.py tests/test_b2341_resume_regression.py tests/test_b2281_stale_regression_protection.py` → **12 passed**.

`node --check web/app.js` i `python -m compileall -q backend scripts` → bez błędów.

**Pełna regresja nie została zakończona.** PostgreSQL, przeglądarki i telefony nadal wymagają testów. Nie podłączano produkcyjnych usług.
