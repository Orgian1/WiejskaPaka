"""Local offer discovery. Coordinates are geographical data, never monetary amounts.

Integer microdegrees at the API/storage boundary; unit-sphere vectors permit
portable SQL distance ordering on SQLite and PostgreSQL without extensions.
Customer coordinates are used only as query parameters and are never persisted.
"""
import math
import unicodedata

EARTH_RADIUS_M = 6_371_008.8
RADII_M = (100, 500, 1000, 5000)
SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS pickup_point_coordinates (
    point_id INTEGER PRIMARY KEY REFERENCES pickup_points(id) ON DELETE CASCADE,
    latitude_e6 INTEGER NOT NULL CHECK(latitude_e6 BETWEEN -90000000 AND 90000000),
    longitude_e6 INTEGER NOT NULL CHECK(longitude_e6 BETWEEN -180000000 AND 180000000),
    sphere_x REAL NOT NULL CHECK(sphere_x BETWEEN -1 AND 1),
    sphere_y REAL NOT NULL CHECK(sphere_y BETWEEN -1 AND 1),
    sphere_z REAL NOT NULL CHECK(sphere_z BETWEEN -1 AND 1)
);
CREATE INDEX IF NOT EXISTS pickup_coordinates_x ON pickup_point_coordinates(sphere_x);
CREATE INDEX IF NOT EXISTS pickup_coordinates_y ON pickup_point_coordinates(sphere_y);
CREATE INDEX IF NOT EXISTS pickup_coordinates_z ON pickup_point_coordinates(sphere_z);
CREATE TABLE IF NOT EXISTS product_search_names (
    product_id INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    name_key TEXT NOT NULL
);
'''


def search_key(text):
    # Polish-aware, accent-insensitive search, including Ł/ł and case folding.
    folded = unicodedata.normalize('NFKD', text.casefold().replace('ł', 'l'))
    return ''.join(c for c in folded if not unicodedata.combining(c))


def index_product(con, product_id, name):
    con.execute('''INSERT INTO product_search_names(product_id,source_name,name_key) VALUES(?,?,?)
        ON CONFLICT(product_id) DO UPDATE SET source_name=excluded.source_name,name_key=excluded.name_key''',
        (product_id, name, search_key(name)))


def refresh_product_index(con, *, postgres=False):
    rows = con.execute('''SELECT p.id,p.name FROM products p
        LEFT JOIN product_search_names s ON s.product_id=p.id
        WHERE s.product_id IS NULL OR s.source_name<>p.name ORDER BY p.id''' + (' FOR UPDATE OF p' if postgres else '')).fetchall()
    for row in rows:
        index_product(con, row['id'], row['name'])
    return len(rows)


def sphere(latitude_e6, longitude_e6):
    if (type(latitude_e6) is not int or type(longitude_e6) is not int
        or not -90_000_000 <= latitude_e6 <= 90_000_000
        or not -180_000_000 <= longitude_e6 <= 180_000_000):
        raise ValueError('Nieprawidłowe współrzędne')
    lat, lon = math.radians(latitude_e6 / 1_000_000), math.radians(longitude_e6 / 1_000_000)
    # At the poles longitude must not cause artificial distance differences.
    if abs(latitude_e6) == 90_000_000:
        return (0.0, 0.0, 1.0 if latitude_e6 > 0 else -1.0)
    if longitude_e6 == 180_000_000:
        lon = -math.pi
    return (math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat))


def save_coordinates(con, point_id, latitude_e6, longitude_e6):
    x,y,z = sphere(latitude_e6, longitude_e6)
    con.execute('''INSERT INTO pickup_point_coordinates(point_id,latitude_e6,longitude_e6,sphere_x,sphere_y,sphere_z)
        VALUES(?,?,?,?,?,?) ON CONFLICT(point_id) DO UPDATE SET latitude_e6=excluded.latitude_e6,
        longitude_e6=excluded.longitude_e6,sphere_x=excluded.sphere_x,sphere_y=excluded.sphere_y,sphere_z=excluded.sphere_z''',
        (point_id,latitude_e6,longitude_e6,x,y,z))


def nearby_offers(con, *, latitude_e6, longitude_e6, radius_m, q='', limit=24, offset=0,
                  min_price_grosze=None, max_price_grosze=None):
    x,y,z = sphere(latitude_e6, longitude_e6)
    if type(radius_m) is not int or radius_m not in RADII_M:
        raise ValueError('Dozwolone promienie: 100, 500, 1000 i 5000 m')
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or not 0 <= offset <= 10000:
        raise ValueError('Nieprawidłowa paginacja')
    chord = 2*math.sin(radius_m/(2*EARTH_RADIUS_M))
    conditions = ['p.stock>0', 't.active=1', "u.role='rolnik'",
                  'c.sphere_x BETWEEN ? AND ?', 'c.sphere_y BETWEEN ? AND ?', 'c.sphere_z BETWEEN ? AND ?']
    params = [x,x,y,y,z,z,x-chord,x+chord,y-chord,y+chord,z-chord,z+chord]
    if q.strip():
        literal = search_key(q.strip()).replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        conditions.append("s.name_key LIKE ? ESCAPE '\\'")
        params.append('%'+literal+'%')
    if min_price_grosze is not None:
        conditions.append('p.price_grosze>=?')
        params.append(min_price_grosze)
    if max_price_grosze is not None:
        conditions.append('p.price_grosze<=?')
        params.append(max_price_grosze)
    sql = '''WITH offers AS (
        SELECT p.id AS product_id,p.farmer_id,p.name AS product_name,p.price_grosze,p.delivery_grosze,p.stock,
        t.id AS point_id,t.name AS point_name,t.city,t.street,t.opening_hours,
        ((c.sphere_x-?)*(c.sphere_x-?)+(c.sphere_y-?)*(c.sphere_y-?)+(c.sphere_z-?)*(c.sphere_z-?)) AS distance_squared
        FROM pickup_point_coordinates c JOIN pickup_points t ON t.id=c.point_id
        JOIN users u ON u.id=t.farmer_id JOIN products p ON p.farmer_id=t.farmer_id
        LEFT JOIN product_search_names s ON s.product_id=p.id
        WHERE ''' + ' AND '.join(conditions) + ''')
        SELECT * FROM offers WHERE distance_squared<=?
        ORDER BY distance_squared,point_id,product_id LIMIT ? OFFSET ?'''
    rows = con.execute(sql, tuple(params+[chord*chord,limit+1,offset])).fetchall()
    items = []
    for row in rows[:limit]:
        distance = 2*EARTH_RADIUS_M*math.asin(min(1.0, math.sqrt(max(0.0,row['distance_squared']))/2))
        items.append({'distance_m':math.ceil(distance),
            'distance_bucket_m':next(r for r in RADII_M if distance<=r+1e-7),
            'product':{key:row[source] for key,source in [('id','product_id'),('farmer_id','farmer_id'),
                ('name','product_name'),('price_grosze','price_grosze'),('delivery_grosze','delivery_grosze'),('stock','stock')]},
            'pickup_point':{key:row[source] for key,source in [('id','point_id'),('name','point_name'),
                ('city','city'),('street','street'),('opening_hours','opening_hours')]}})
    return {'items':items,'radius_m':radius_m,'limit':limit,'offset':offset,'has_more':len(rows)>limit}
