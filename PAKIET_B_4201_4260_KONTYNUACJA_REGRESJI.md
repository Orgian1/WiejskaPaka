# WiejskaPaka — B/4201–B/4260: wznowiona regresja

Wznowiono regresję na podstawie checkpointu z B/4141–B/4200. Każdy moduł testowy jest wykonywany w oddzielnym procesie i na izolowanej testowej bazie SQLite.

- Grupy 6–8: 24/24 moduły zaliczone wcześniej, zweryfikowane w checkpointcie.
- Grupa 9: zakończona, 8/8 (6 nowych zaliczeń).
- Grupa 10: zakończona, 8/8 (8 nowych zaliczeń).
- Grupa 11: zakończona, 8/8 (8 nowych zaliczeń).
- Grupa 12: 2/8 ukończone i zaliczone przed limitem czasu.
- Łącznie checkpoint: 50 zaliczonych modułów, 0 wykrytych błędów w wykonanych modułach.
- Łącznie w tym wznowieniu: 24 dodatkowe zaliczone moduły (grupa 9: 6, grupa 10: 8, grupa 11: 8, grupa 12: 2).
- W manifeście jest 211 modułów testowych; nie jest to jeszcze pełna regresja. Nie wszystkie 2805 przypadków testowych zostały uruchomione.
- Kontrola składni JS i kompilacji Python zakończona pomyślnie.
- PostgreSQL, testy przeglądarkowe i telefony pozostają nieprzetestowane.
- Bez zmian w Neon, domenie, hostingu i płatnościach produkcyjnych.

Checkpoint: `REGRESJA_B_4141_4200_WYNIKI.json`.

Wznowienie:

```bash
python scripts/run_regression_chunks.py --batch-size 8 --timeout 25 --start-batch 6 --resume --report REGRESJA_B_4141_4200_WYNIKI.json
```
