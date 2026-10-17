# Etap 18 — zweryfikowana sesja i transakcja PostgreSQL

Dodano `postgres_verified_db(url, authorization, now=None)` w `backend/pg_adapter.py`.
Funkcja otwiera połączenie i transakcję, weryfikuje token Bearer w tabeli
`sessions`, a następnie ustawia `wiejskapaka.actor_id` przez `set_config(..., true)`.
Wszystkie zapytania w bloku `with` używają tego samego połączenia i transakcji.
Po zakończeniu kontekst aktora jest czyszczony, a błędy powodują rollback.

Przykład wewnętrzny (token z nagłówka Authorization, nigdy actor_id od klienta):

```python
from backend.pg_adapter import postgres_verified_db
with postgres_verified_db(database_url, authorization_header) as (con, actor_id):
    rows = con.execute('SELECT id FROM orders WHERE buyer_id=%s', (actor_id,)).fetchall()
```

**Ograniczenia:** funkcja jest gotowa do stopniowej integracji, ale istniejące
endpointy FastAPI nadal używają własnego `db()` i `current_user()`; nie są
jeszcze przeniesione na ten mechanizm. RLS pozostaje wyłączony. Custom GUC
`wiejskapaka.actor_id` nie jest samodzielną granicą bezpieczeństwa wobec
kompromitacji konta bazy, które może ustawić tę wartość. Przed uruchomieniem
RLS należy zaprojektować polityki, uprawnienia ról i przetestować je na
odizolowanej bazie PostgreSQL/Neon. Nie wykonywano operacji na Neon ani
publicznej stronie. Płatności produkcyjne są wyłączone.

Testy lokalne: 1281 passed, 3 skipped, 16 subtests passed.
