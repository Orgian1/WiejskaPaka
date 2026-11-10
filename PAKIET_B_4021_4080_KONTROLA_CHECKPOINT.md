# B/4021–B/4080 — kontrola integralności wznowienia regresji

- Weryfikacja checkpointów regresji: odmowa wznowienia, jeśli raport zawiera powtórzone grupy, powtórzone moduły lub moduły nieprzynależne do grupy.
- Nowe testy źródłowe: 2/2 zaliczone.
- Rozpoczęto regresję izolowaną grupy 2 (8 modułów). W raporcie zapisano 7 zaliczonych modułów; proces został przerwany limitem czasu przed ósmym. Nie jest to pełna regresja.
- `python -m compileall -q backend scripts` i `node --check web/app.js` zakończone bez błędów.
- Bez zmian Neon, hostingu, domeny, płatności rzeczywistych.
