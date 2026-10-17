# B/3841–B/3900 — checkpoint regresji

Uruchomiono izolowany przebieg pierwszej grupy testów z limitem 8 s na moduł. Proces nadrzędny przekroczył czas dostępny w środowisku, lecz raport JSON zapisany atomowo zachował wyniki **10 zaliczonych modułów**. Raport ma `complete: false` oraz `in_progress: true`. Nie stanowi dowodu ukończenia regresji 2805 przypadków.

Dodano `scripts/summarize_regression_progress.py` do bezpiecznego zliczania zaliczonych/niezaliczonych modułów w raportach częściowych. Testy nowego narzędzia: 2/2 PASS. Sprawdzono `node --check web/app.js` i `python -m compileall -q backend scripts`.

Kolejne uruchomienie: `python scripts/run_regression_chunks.py --batch-size 12 --timeout 8 --only-batch 1 --report regression_3841_batch1.json --resume` (wyniki zachowane dla zgodnych kodu i zestawu testów). Uwaga: nowy skrypt zmienia fingerprint kodu, więc po jego dodaniu istniejącego raportu nie należy wznawiać bez nowego przebiegu. Raport zachowano wyłącznie jako historyczny dowód wykonania przed zmianą.

Nie zmieniano płatności, konfiguracji Neon ani hostingu.
