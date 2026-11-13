"""Reversible listing visibility; stock and historical orders are never deleted."""
from fastapi import HTTPException

SCHEMA_SQLITE = '''CREATE TABLE IF NOT EXISTS product_listing_states(
 product_id INTEGER PRIMARY KEY REFERENCES products(id),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);'''


def active(con, product_id):
    row = con.execute('SELECT active FROM product_listing_states WHERE product_id=?', (product_id,)).fetchone()
    return row is None or bool(row['active'])


def require_active(con, product_id):
    if not active(con, product_id):
        raise HTTPException(409, 'Oferta jest wycofana. Wybierz inny produkt.')


def metadata(con, product_id):
    return {'listing_active': active(con, product_id)}
