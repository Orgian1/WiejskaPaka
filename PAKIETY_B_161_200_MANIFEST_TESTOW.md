# WiejskaPaka B/161–B/200 — kontrola integralności testów (zakres rzeczywiście wykonany)

Nowy moduł `scripts/regression_manifest.py` wylicza SHA-256 dla plików testowych oraz całego manifestu, wykrywa zmiany plików i odrzuca dowiązania symboliczne oraz katalogi udające testy. Runner `scripts/run_regression_chunks.py` sprawdza listę wybranych testów i zapisuje sumę kontrolną manifestu oraz liczbę plików w raporcie. Dodano 11 testów automatycznych.

Uwaga: nazwa B/161–B/200 jest numeracją pakietu roboczego, **nie** oznacza 40 niezależnych ukończonych funkcjonalności. Nie zmieniano schematu Neon, płatności, RLS ani produkcyjnych danych. Manifest opisuje zestaw testów, nie potwierdza sam w sobie pomyślnej regresji całej aplikacji.

Uruchom: `python -m pytest -q tests/test_b161_b200_manifest.py`.

Regresja wybranych modułów diagnostycznych: **62 passed** (w tym 11 nowych testów). Poprawiono kompatybilność z testami wykorzystującymi tymczasowy katalog projektu.
