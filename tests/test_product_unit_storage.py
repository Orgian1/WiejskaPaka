import sqlite3

import pytest

from backend.product_unit_storage import (
    SCHEMA_SQLITE, capture_order_unit, insert_product_unit, product_unit,
)


@pytest.fixture
def con():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.executescript('''
      CREATE TABLE products(id INTEGER PRIMARY KEY,stock INTEGER NOT NULL);
      CREATE TABLE orders(id INTEGER PRIMARY KEY,product_id INTEGER REFERENCES products(id),quantity INTEGER);
      CREATE TABLE saved_cart_items(product_id INTEGER REFERENCES products(id));
      INSERT INTO products VALUES(1,7),(2,9);
    ''' + SCHEMA_SQLITE)
    yield connection
    connection.close()


def test_legacy_product_remains_pieces_without_changing_stock(con):
    assert product_unit(con, 1) == {'sale_unit': 'szt', 'package_content': None}
    assert con.execute('SELECT stock FROM products WHERE id=1').fetchone()['stock'] == 7


def test_packaging_and_immutable_order_snapshot(con):
    insert_product_unit(con, 1, 'worek', '15', 'kg')
    assert product_unit(con, 1)['package_content'] == {'amount_atoms': 15000, 'unit': 'kg'}
    con.execute('INSERT INTO orders VALUES(1,1,2)')
    capture_order_unit(con, 1)
    assert dict(con.execute('SELECT * FROM order_sale_units').fetchone()) == {
        'order_id': 1, 'unit': 'worek', 'content_json': '{"amount_atoms":15000,"unit":"kg"}',
    }
    for query in ('UPDATE order_sale_units SET unit=\'szt\'', 'DELETE FROM order_sale_units'):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(query)


def test_product_unit_cannot_change_or_be_replaced(con):
    insert_product_unit(con, 1, 'kg')
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE product_sale_units SET unit='szt' WHERE product_id=1")
    with pytest.raises(sqlite3.IntegrityError):
        insert_product_unit(con, 1, 'szt')
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT OR REPLACE INTO product_sale_units VALUES(1,'szt',NULL)")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute('DELETE FROM product_sale_units WHERE product_id=1')


@pytest.mark.parametrize('table', ['orders', 'saved_cart_items'])
def test_cannot_reinterpret_listing_already_in_use(con, table):
    if table == 'orders':
        con.execute('INSERT INTO orders VALUES(1,1,2)')
    else:
        con.execute('INSERT INTO saved_cart_items VALUES(1)')
    with pytest.raises(ValueError):
        insert_product_unit(con, 1, 'kg')
    assert product_unit(con, 1)['sale_unit'] == 'szt'


def test_metadata_and_checkout_roll_back_together(con):
    con.commit()
    con.execute('BEGIN')
    insert_product_unit(con, 1, 'kg')
    con.execute('INSERT INTO orders VALUES(1,1,2)')
    capture_order_unit(con, 1)
    con.rollback()
    assert product_unit(con, 1)['sale_unit'] == 'szt'
    assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 0
    assert con.execute('SELECT COUNT(*) FROM order_sale_units').fetchone()[0] == 0


def test_no_orphan_metadata(con):
    with pytest.raises(sqlite3.IntegrityError):
        insert_product_unit(con, 999, 'kg')


def test_missing_order_cannot_be_snapshotted(con):
    with pytest.raises(ValueError):
        capture_order_unit(con, 999)
