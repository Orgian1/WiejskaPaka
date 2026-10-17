# WiejskaPaka B/4381–B/4440 — kontynuacja regresji

Kontynuowano regresję z checkpointu 110/211 modułów. Podczas przebiegu z limitem 15 sekund moduł `test_regression_diagnostics_b116_b120.py` przekroczył limit; uruchomiony samodzielnie zakończył się wynikiem 5/5 w 14,74 s. Powtórny przebieg z limitem 35 sekund na moduł zaliczył ten moduł (ok. 17 s) i kolejne partie.

Stan końcowy jest zapisany w `REGRESJA_B_4141_4200_WYNIKI.json`. Wznowienie: `python scripts/run_regression_chunks.py --batch-size 8 --timeout 35 --start-batch 6 --resume --report REGRESJA_B_4141_4200_WYNIKI.json`.

Pełna regresja, testy PostgreSQL i testy na urządzeniach pozostają nieukończone. Nie zmieniano aplikacji, konfiguracji Neon ani płatności produkcyjnych.
