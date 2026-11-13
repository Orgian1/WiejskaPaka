"""Classification migration adds metadata only; reruns preserve seller corrections."""
import sqlite3
from backend.product_categories import schema_sql


def test_existing_products_photos_orders_prices_and_stock_survive():
    con=sqlite3.connect(':memory:');con.execute('PRAGMA foreign_keys=ON')
    con.executescript('CREATE TABLE products(id INTEGER PRIMARY KEY,name TEXT,price_grosze INTEGER,stock INTEGER);CREATE TABLE photos(product_id INTEGER,data BLOB);CREATE TABLE orders(id INTEGER,product_id INTEGER,total_grosze INTEGER);')
    con.executemany('INSERT INTO products VALUES(?,?,?,?)',[(1,'Pomidory',299,5),(2,'Miód lipowy',1201,0),(3,'Pomidory i ogórki',999,4),(4,'Dżem niespodzianka',501,3)])
    con.execute("INSERT INTO photos VALUES(1,X'0001FEFF')");con.execute('INSERT INTO orders VALUES(1,1,299)')
    before={t:con.execute('SELECT * FROM '+t).fetchall() for t in ['products','photos','orders']}
    con.executescript(schema_sql())
    assert con.execute('SELECT product_id,category_id FROM product_classifications ORDER BY product_id').fetchall()==[(1,'vegetables'),(2,'honey'),(3,'other'),(4,'other')]
    con.execute("UPDATE product_classifications SET category_id='preserves',subcategory_id='preserves-jams',description='Ręcznie poprawione' WHERE product_id=4")
    con.executescript(schema_sql())
    assert con.execute('SELECT description FROM product_classifications WHERE product_id=4').fetchone()[0]=='Ręcznie poprawione'
    assert before=={t:con.execute('SELECT * FROM '+t).fetchall() for t in before}
    assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
