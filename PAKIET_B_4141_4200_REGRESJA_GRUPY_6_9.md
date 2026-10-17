# WiejskaPaka — B/4141–B/4200: regresja grup 6–9

Przeprowadzono izolowaną regresję, uruchamiając każdy moduł pytest w osobnym procesie z osobną testową bazą SQLite.

- Grupa 6: 8/8 modułów zaliczonych.
- Grupa 7: 8/8 modułów zaliczonych.
- Grupa 8: 8/8 modułów zaliczonych.
- Grupa 9: 2/8 modułów zaliczone przed przerwaniem przebiegu.
- **Razem 26/26 ukończonych modułów bez błędów.** Pozostałe 6 modułów grupy 9 nie zostało jeszcze sprawdzonych w tym przebiegu.
- Wyniki zapisano w `REGRESJA_B_4141_4200_WYNIKI.json`. Plik zawiera checkpoint umożliwiający wznowienie z opcją `--resume`.
- Nie jest to zakończona pełna regresja. Nie testowano PostgreSQL ani fizycznych telefonów.
- Nie zmieniano Neon, hostingu, domeny ani płatności produkcyjnych.

Wznowienie:

```bash
python scripts/run_regression_chunks.py --batch-size 8 --timeout 25 --start-batch 6 --resume --report REGRESJA_B_4141_4200_WYNIKI.json
```
