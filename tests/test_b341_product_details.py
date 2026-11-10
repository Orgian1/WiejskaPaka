import sqlite3
from contextlib import contextmanager
import pytest
from fastapi import HTTPException
from backend import app as api

@pytest.fixture
def catalog(tmp_path, monkeypatch):
    con = sqlite3.connect(tmp_path / 'catalog.sqlite3')
    con.row_factory = sqlite3.Row
    con.execute('CREATE TABLE products(id INTEGER PRIMARY KEY, farmer_id INTEGER, name TEXT, price_grosze INTEGER, delivery_grosze INTEGER, stock INTEGER)')
    con.executemany('INSERT INTO products VALUES (?,?,?,?,?,?)', [(1,3,'Miód',2300,500,4),(2,3,'Ser',1500,0,0)])
    con.commit()
    @contextmanager
    def db():
        yield con
    monkeypatch.setattr(api, 'db', db)
    yield
    con.close()

def test_available_product_details(catalog):
    result = api.product_details(1)
    assert result == {'id':1,'farmer_id':3,'name':'Miód','price_grosze':2300,'delivery_grosze':500,'stock':4}

def test_out_of_stock_not_public(catalog):
    with pytest.raises(HTTPException) as exc:
        api.product_details(2)
    assert exc.value.status_code == 404

@pytest.mark.parametrize('product_id', [-1,0,999])
def test_invalid_or_missing_product(catalog,product_id):
    with pytest.raises(HTTPException) as exc:
        api.product_details(product_id)
    assert exc.value.status_code == 404
