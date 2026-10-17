from contextlib import contextmanager
import sqlite3
import pytest
from fastapi import HTTPException
from backend import app as api

@pytest.fixture
def store(tmp_path, monkeypatch):
    conn = sqlite3.connect(tmp_path / 'edit.sqlite')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE products(id INTEGER PRIMARY KEY, farmer_id INTEGER, name TEXT, price_grosze INTEGER, delivery_grosze INTEGER, stock INTEGER CHECK(stock>=0))')
    conn.executemany('INSERT INTO products VALUES(?,?,?,?,?,?)', [(1,10,'Marchew',100,0,5),(2,20,'Jablka',200,0,7)])
    from backend.local_marketplace import SCHEMA_SQLITE
    conn.executescript(SCHEMA_SQLITE)
    conn.commit()
    @contextmanager
    def write(*args, **kwargs):
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    monkeypatch.setattr(api, 'order_write_db', write)
    yield conn
    conn.close()

def update(id, farmer, **fields):
    return api.update_my_product(id, api.ProductUpdateIn(**fields), {'id':farmer,'role':'rolnik'}, 'Bearer test')

def test_owner_updates_selected_fields(store):
    result = update(1,10,stock=12,price_grosze=125)
    assert (result['stock'],result['price_grosze'],result['name']) == (12,125,'Marchew')

def test_other_farmer_cannot_update(store):
    with pytest.raises(HTTPException) as exc:
        update(2,10,stock=99)
    assert exc.value.status_code == 404
    assert store.execute('SELECT stock FROM products WHERE id=2').fetchone()[0] == 7

def test_empty_update_rejected(store):
    with pytest.raises(HTTPException) as exc:
        update(1,10)
    assert exc.value.status_code == 422

def test_explicit_null_rejected(store):
    with pytest.raises(HTTPException) as exc:
        update(1,10,name=None)
    assert exc.value.status_code == 422

def test_stock_limits_enforced():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        api.ProductUpdateIn(stock=-1)

def test_customer_cannot_edit(store):
    with pytest.raises(HTTPException) as exc:
        api.update_my_product(1,api.ProductUpdateIn(stock=2),{'id':10,'role':'klient'},'Bearer test')
    assert exc.value.status_code == 403
