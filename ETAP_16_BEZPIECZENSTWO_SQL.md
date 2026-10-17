# Etap 16 — audyt zapytań SQL przed RLS

To jest **statyczny inwentarz do przeglądu**, nie wdrożenie RLS.

## Odwołania do tabel wrażliwych

### delivery_assignments (10 wystąpień)
- `app.py:309` — READ
- `app.py:432` — READ
- `app.py:485` — READ
- `app.py:508` — READ
- `app.py:511` — WRITE
- `app.py:526` — READ
- `app.py:539` — READ
- `app.py:549` — READ
- `app.py:1382` — READ
- `neon_order_access.py:33` — READ

### order_locations (4 wystąpień)
- `app.py:271` — WRITE
- `app.py:432` — READ
- `app.py:1382` — READ
- `neon_order_access.py:33` — READ

### orders (23 wystąpień)
- `app.py:270` — WRITE
- `app.py:287` — READ
- `app.py:289` — READ
- `app.py:321` — WRITE
- `app.py:323` — WRITE
- `app.py:339` — WRITE
- `app.py:372` — WRITE
- `app.py:432` — READ
- `app.py:471` — READ
- `app.py:529` — WRITE
- `app.py:536` — READ
- `app.py:549` — READ
- `app.py:613` — READ
- `app.py:1047` — READ
- `app.py:1072` — READ
- `app.py:1382` — READ
- `neon_order_access.py:16` — READ
- `neon_order_access.py:24` — READ
- `neon_order_access.py:33` — READ
- `payout_batches.py:40` — READ
- `payout_reconciliation.py:10` — READ
- `payout_reports.py:35` — READ
- `seller_compliance.py:27` — READ

### seller_compliance (4 wystąpień)
- `seller_compliance.py:25` — READ
- `seller_compliance.py:39` — READ
- `seller_compliance.py:42` — WRITE
- `seller_compliance.py:51` — WRITE

### sessions (5 wystąpień)
- `app.py:169` — READ
- `app.py:222` — WRITE
- `app.py:232` — WRITE
- `app.py:461` — WRITE
- `neon_session_bridge.py:37` — READ

### users (12 wystąpień)
- `app.py:169` — READ
- `app.py:189` — WRITE
- `app.py:205` — READ
- `app.py:505` — READ
- `app.py:1155` — READ
- `app.py:1200` — READ
- `app.py:1239` — READ
- `app.py:1257` — READ
- `app.py:1280` — READ
- `app.py:1368` — READ
- `neon_session_bridge.py:37` — READ
- `payout_scheduler.py:24` — READ

Zapytania dynamiczne wymagające ręcznego przeglądu: **11**.

## Blokady wdrożenia
- Statyczna analiza nie wykrywa wszystkich zapytań budowanych dynamicznie.
- Wykrycie WHERE ani zależności sesji nie dowodzi autoryzacji.
- Wspólny login SQL i ustawialny GUC nie stanowią samodzielnej granicy bezpieczeństwa.
- Nie uruchamiać RLS bez testów integracyjnych i polityk zapisu.
- Brak potwierdzonego połączenia i testów na prawdziwym Neon PostgreSQL.
- RLS pozostaje wyłączony, płatności produkcyjne nieaktywne, strona publiczna bez zmian.
