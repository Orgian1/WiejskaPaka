from fastapi.testclient import TestClient
from backend import app as module


def test_search_filters_and_pagination(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'DATABASE_URL', '')
    monkeypatch.setattr(module, 'DB_PATH', str(tmp_path / 'catalog.sqlite3'))
    module.init_db()
    with module.db() as con:
        con.execute("INSERT INTO users(id,email,password_hash,role) VALUES(1,'farmer@example.test','x','rolnik')")
        con.executemany('INSERT INTO products(farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(1,?,?,0,?)',
                        [('Jabłka', 300, 10), ('Gruszki', 450, 2), ('Jabłka bio', 500, 0), ('100% sok', 250, 3)])
    from backend.local_marketplace import SCHEMA_SQLITE, refresh_product_index
    with module.db() as con:
        con.executescript(SCHEMA_SQLITE)
        refresh_product_index(con)
    client = TestClient(module.app)
    data = client.get('/catalog/search', params={'q': 'jabł', 'limit': 1}).json()
    assert data['total'] == 1 and len(data['items']) == 1
    assert client.get('/catalog/search', params={'q': '%'}).json()['total'] == 1
    assert client.get('/catalog/search', params={'min_price_grosze': 400}).json()['total'] == 1
    assert client.get('/catalog/search', params={'limit': 101}).status_code == 422
    assert client.get('/catalog/search', params={'min_price_grosze': 500, 'max_price_grosze': 100}).status_code == 422
