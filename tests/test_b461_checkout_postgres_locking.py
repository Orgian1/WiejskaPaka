"""Contract regression: PostgreSQL checkout locks the cart and stock rows."""
from pathlib import Path
from backend.pg_adapter import translate_sql


def test_checkout_uses_row_locks_for_postgres():
    source = (Path(__file__).resolve().parents[1] / 'backend' / 'app.py').read_text()
    start = source.index("@app.post('/cart/checkout-test'")
    end = source.index("@app.post('/orders'", start)
    checkout = source[start:end]
    assert "(' FOR UPDATE OF c,p' if DATABASE_URL else '')" in checkout
    assert "with order_write_db(user, authorization, ('klient',))" in checkout
    from backend import app
    import inspect
    transaction=inspect.getsource(app.order_write_db).split('    else:', 1)[1]
    assert transaction.index('BEGIN IMMEDIATE')<transaction.index('authorize_transaction(')<transaction.index('yield con')
    assert "con.execute('BEGIN' if DATABASE_URL" not in checkout


def test_postgres_row_lock_translation():
    sql = 'SELECT c.product_id FROM saved_cart_items c JOIN products p ON p.id=c.product_id WHERE c.buyer_id=? ORDER BY c.product_id FOR UPDATE OF c,p'
    translated = translate_sql(sql)
    assert '%s' in translated
    assert translated.endswith('FOR UPDATE OF c,p')
