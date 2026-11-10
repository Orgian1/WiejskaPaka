# WiejskaPaka B/6121–B/6180 — rozszerzone kontrole koszyka HTTP

Data: 2026-10-15. Środowisko: lokalny FastAPI/Uvicorn na 127.0.0.1, jednorazowe SQLite, płatności wyłącznie testowe.

## Zmiany
Rozszerzono `scripts/check_http_multi_seller_cart.py` o kontrole:
- Odbiór osobisty produktów od dwóch rolników: zero opłat dostawy, oddzielne przesyłki, poprawna suma 2468 groszy.
- Odrzucenie powtórzonego produktu w wycenie (HTTP 422).
- Odrzucenie zamówienia ponad dostępny stan magazynowy (HTTP 409).
- Wycena publicznie dostępnych produktów przez innego klienta, bez dostępu do prywatnego koszyka właściciela.
- Zakaz wyceny koszyka klienta dla roli rolnik (HTTP 403).

## Wykonane testy
- `python scripts/check_http_multi_seller_cart.py`: PASS, 36 kontroli.
- `python scripts/check_http_checkout_e2e.py`: PASS, 34 kontrole.
- `python -m compileall -q backend scripts`: PASS.
- `node --check web/app.js`: PASS.

Nie przeprowadzono testów z rzeczywistą bazą PostgreSQL, z przeglądarką Chromium połączoną przez HTTP ani na fizycznym telefonie. Nie podłączono Neon, hostingu, domeny ani prawdziwych płatności.
