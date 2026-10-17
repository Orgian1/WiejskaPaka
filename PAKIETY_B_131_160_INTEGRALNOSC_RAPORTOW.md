# WiejskaPaka — B/131–B/160: integralność raportów regresji

Dodano `scripts/analyze_regression_report.py` — niezależny, lokalny weryfikator raportów JSON z `scripts/run_regression_chunks.py`. Weryfikuje format, numery i kolejność pakietów, listy plików testowych, statusy procesów, timeouty, czas wykonania oraz prawdziwość deklaracji `complete`. Raporty niekompletne nie są oznaczane jako pełny sukces. Narzędzie nie łączy się z Neon, bazą produkcyjną ani usługami płatniczymi.

Dodano 31 automatycznych testów (pakiet B/131–B/160 z dodatkowym testem kontrolnym). Testy łącznie z trzema poprzednimi modułami: **51 passed**. Nie jest to wynik pełnej regresji aplikacji.

Uruchomienie:

```bash
python scripts/analyze_regression_report.py regression_batches_report.json --json
python -m pytest -q tests/test_b131_b160_report_integrity.py tests/test_b121_b130_runner_hardening.py tests/test_regression_diagnostics_b116_b120.py tests/test_regression_runner_b101_b105.py
```

Status: lokalna diagnostyka; nie wdrożono RLS ani produkcyjnych płatności; Neon niezmieniony.
