# WiejskaPaka B/6001–B/6060 — jedna opłata dostawy za przesyłkę

## Zmiany
- Rozszerzono rzeczywisty test TCP HTTP (`scripts/check_http_checkout_e2e.py`) o zamówienie **2 sztuk jednego produktu w jednej przesyłce**.
- Weryfikacja: 2 × 349 gr + **jedna** opłata dostawy 501 gr = **1199 gr** (nie 1700 gr).
- Dodano kontrole kwoty w całkowitych groszach, braku dostępu obcego użytkownika i nieprzypisanego kuriera do adresu oraz zakazu wysłania przesyłki przez klienta.
- Rozszerzono `tests/test_http_checkout_e2e_b5941.py` o odrębny test regresyjny nowego scenariusza.

## Wyniki
- `HTTP_CHECKOUT_E2E_REPORT_B6001.json`: 34/34 kontroli PASS.
- `TESTY_B_6001_6060.txt`: 5/5 testów PASS.
- `node --check web/app.js`: PASS.
- `python -m compileall -q backend scripts`: PASS.

## Ograniczenia
- Test obejmuje wiele sztuk **tego samego produktu**, nie pełny koszyk wielu różnych produktów ani wielosprzedawcowe przesyłki.
- Serwer FastAPI działał na localhost z jednorazową SQLite i wyłącznie symulowanymi płatnościami.
- Nie testowano rzeczywistego PostgreSQL ani przeglądarki połączonej z HTTP.
- Nie podłączano Neon, hostingu, domeny ani produkcyjnych płatności.
