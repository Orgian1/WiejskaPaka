"""Private, persistent account favorites; no public customer directory."""
from pydantic import BaseModel, Field


class SavedLocationIn(BaseModel):
    latitude_e6: int = Field(strict=True, ge=-90000000, le=90000000)
    longitude_e6: int = Field(strict=True, ge=-180000000, le=180000000)


from fastapi import Depends, Header, HTTPException, Query

SCHEMA = '''CREATE TABLE IF NOT EXISTS account_favorites (
 user_id INTEGER NOT NULL REFERENCES users(id),
 product_id INTEGER NOT NULL REFERENCES products(id),
 PRIMARY KEY(user_id, product_id)
)'''


def install(app, db, write_db, current_user, database_url):
    if not database_url:
        with db() as con:
            con.execute(SCHEMA)
            con.execute('''CREATE TABLE IF NOT EXISTS account_saved_locations (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                latitude_e6 INTEGER NOT NULL CHECK(latitude_e6 BETWEEN -90000000 AND 90000000),
                longitude_e6 INTEGER NOT NULL CHECK(longitude_e6 BETWEEN -180000000 AND 180000000))''')

    @app.get('/favorites')
    def favorites(user=Depends(current_user), authorization: str | None = Header(default=None),
                  limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0, le=10000)):
        with write_db(user, authorization, ('klient', 'rolnik')) as con:
            rows=con.execute('''SELECT p.* FROM products p JOIN account_favorites f ON f.product_id=p.id
                WHERE f.user_id=? ORDER BY p.id DESC LIMIT ? OFFSET ?''', (user['id'],limit+1,offset)).fetchall()
            return {'items':[dict(r) for r in rows[:limit]], 'has_more':len(rows)>limit, 'offset':offset}

    @app.put('/favorites/{product_id}')
    def add_favorite(product_id: int, user=Depends(current_user), authorization: str | None = Header(default=None)):
        with write_db(user, authorization, ('klient', 'rolnik')) as con:
            if not con.execute('SELECT id FROM products WHERE id=?',(product_id,)).fetchone():
                raise HTTPException(404,'Brak produktu')
            con.execute('INSERT INTO account_favorites(user_id,product_id) VALUES(?,?) ON CONFLICT(user_id,product_id) DO NOTHING',
                        (user['id'],product_id))
        return {'favorite': True}

    @app.delete('/favorites/{product_id}')
    def remove_favorite(product_id: int, user=Depends(current_user), authorization: str | None = Header(default=None)):
        with write_db(user, authorization, ('klient', 'rolnik')) as con:
            con.execute('DELETE FROM account_favorites WHERE user_id=? AND product_id=?',(user['id'],product_id))
        return {'favorite': False}

    @app.get('/account/location')
    def saved_location(user=Depends(current_user), authorization: str | None = Header(default=None)):
        with write_db(user, authorization, ('klient', 'rolnik')) as con:
            row=con.execute('SELECT latitude_e6,longitude_e6 FROM account_saved_locations WHERE user_id=?',(user['id'],)).fetchone()
            return {'location':dict(row) if row else None}

    @app.put('/account/location')
    def save_location(payload: SavedLocationIn, user=Depends(current_user), authorization: str | None = Header(default=None)):
        with write_db(user, authorization, ('klient', 'rolnik')) as con:
            con.execute("""INSERT INTO account_saved_locations(user_id,latitude_e6,longitude_e6) VALUES(?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET latitude_e6=excluded.latitude_e6,longitude_e6=excluded.longitude_e6""",
                (user['id'],payload.latitude_e6,payload.longitude_e6))
        return {'saved':True}

    @app.delete('/account/location')
    def clear_location(user=Depends(current_user), authorization: str | None = Header(default=None)):
        with write_db(user, authorization, ('klient', 'rolnik')) as con:
            con.execute('DELETE FROM account_saved_locations WHERE user_id=?',(user['id'],))
        return {'saved':False}
