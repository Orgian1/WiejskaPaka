"""Public saved-location lookup: no geocoder, no inactive/private points."""
import sqlite3
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.address_search import local_router


def client(tmp_path):
    path = tmp_path / 'locations.sqlite'
    con = sqlite3.connect(path)
    con.executescript('''
        CREATE TABLE pickup_points(id INTEGER PRIMARY KEY,name TEXT,city TEXT,street TEXT,active INTEGER);
        CREATE TABLE pickup_point_coordinates(point_id INTEGER,latitude_e6 INTEGER,longitude_e6 INTEGER);
        INSERT INTO pickup_points VALUES
          (1,'Rynek','ŁÓDŹ','Polna 1',1),
          (2,'Ukryty','ŁÓDŹ','Polna 2',0),
          (3,'Bez mapy','ŁÓDŹ','Polna 3',1),
          (4,'Inne','Legnica','Polna 4',1);
        INSERT INTO pickup_point_coordinates VALUES (1,51000000,16000000),(2,51000001,16000001),(4,51000002,16000002);
    ''')
    con.close()

    @contextmanager
    def connect():
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        try:
            yield con
        finally:
            con.close()

    app = FastAPI()
    app.include_router(local_router(connect))
    return TestClient(app)


def test_only_active_geolocated_points_and_polish_casefold(tmp_path):
    response = client(tmp_path).post('/address-search/pickup-locations', json={'city':'łódź','street':'pol'})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    items = response.json()['items']
    assert len(items) == 1
    assert items[0]['label'] == 'ŁÓDŹ, Polna 1 — Rynek'
    assert items[0]['latitude_e6'] == 51000000
    assert 'nie od Twojego domu' in items[0]['notice']


def test_wildcards_are_literal_and_postcode_is_not_silently_ignored(tmp_path):
    c = client(tmp_path)
    for body in ({'city':'Ł%'}, {'city':"Łódź' OR 1=1 --"}, {'city':'Łódź','postal_code':'90-001'}):
        response = c.post('/address-search/pickup-locations',json=body)
        assert response.status_code == 200
        assert response.json()['items'] == []


def test_bound_validation_and_result_limit(tmp_path):
    c = client(tmp_path)
    assert c.post('/address-search/pickup-locations',json={'city':'Łódź','url':'https://unexpected.invalid'}).status_code == 422
    con = sqlite3.connect(tmp_path / 'locations.sqlite')
    for point in range(10,20):
        con.execute('INSERT INTO pickup_points VALUES(?,?,?,?,1)',(point,'Punkt','ŁÓDŹ','Polna'))
        con.execute('INSERT INTO pickup_point_coordinates VALUES(?,?,?)',(point,51000000,16000000))
    con.commit()
    con.close()
    assert len(c.post('/address-search/pickup-locations',json={'city':'Łódź'}).json()['items']) == 5
