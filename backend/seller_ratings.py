"""Immutable buyer ratings for orders actually collected with the existing PIN flow."""
from fastapi import Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from backend.order_mail_outbox import _postgres

SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS seller_ratings (
 order_id BIGINT PRIMARY KEY REFERENCES orders(id),
 buyer_id BIGINT NOT NULL REFERENCES users(id),
 farmer_id BIGINT NOT NULL REFERENCES users(id),
 stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS seller_ratings_farmer ON seller_ratings(farmer_id);
'''
SQLITE_IMMUTABLE='''
CREATE TRIGGER IF NOT EXISTS seller_ratings_no_update BEFORE UPDATE ON seller_ratings
BEGIN SELECT RAISE(ABORT,'Ratings are immutable'); END;
CREATE TRIGGER IF NOT EXISTS seller_ratings_no_delete BEFORE DELETE ON seller_ratings
BEGIN SELECT RAISE(ABORT,'Ratings are immutable'); END;
'''

class Rating(BaseModel):
    model_config={'extra':'forbid'}
    stars:int=Field(strict=True,ge=1,le=5)


def summary(con,farmer_id):
    if _postgres(con) and con.gateway:
        row=con.execute('SELECT * FROM wp_rls.seller_rating_summary(?)',(farmer_id,)).fetchone()
    else:
        row=con.execute('SELECT COUNT(*) AS count,COALESCE(SUM(stars),0) AS total FROM seller_ratings WHERE farmer_id=?',(farmer_id,)).fetchone()
    count=row['count'];total=row['total']
    return {'farmer_id':farmer_id,'count':count,'average':round(total/count,2) if count else None}


def install(app,db,write_db,current_user,database_url):
    if not database_url:
        with db() as con:con.executescript(SCHEMA_SQLITE+SQLITE_IMMUTABLE)

    @app.get('/farmers/{farmer_id}/ratings')
    def public_summary(farmer_id:int):
        if farmer_id<1:raise HTTPException(404,'Nie znaleziono sprzedawcy')
        with db() as con:
            seller=con.execute("SELECT id FROM users WHERE id=? AND role='rolnik'",(farmer_id,)).fetchone()
            if not seller:raise HTTPException(404,'Nie znaleziono sprzedawcy')
            return summary(con,farmer_id)

    @app.get('/orders/{order_id}/seller-rating')
    def own_rating(order_id:int,user=Depends(current_user)):
        if user['role']!='klient':raise HTTPException(403,'Tylko kupujący może ocenić zakup')
        with db() as con:
            order=con.execute('SELECT buyer_id,farmer_id FROM orders WHERE id=? AND buyer_id=?',(order_id,user['id'])).fetchone()
            if not order:raise HTTPException(404,'Nie znaleziono zamówienia')
            row=con.execute('SELECT stars FROM seller_ratings WHERE order_id=? AND buyer_id=?',(order_id,user['id'])).fetchone()
        return {'order_id':order_id,'farmer_id':order['farmer_id'],'stars':row['stars'] if row else None}

    @app.post('/orders/{order_id}/seller-rating')
    def rate(order_id:int,payload:Rating,authorization:str=Header(default=''),user=Depends(current_user)):
        with write_db(user,authorization,('klient',)) as con:
            suffix=' FOR UPDATE' if _postgres(con) else ''
            order=con.execute('SELECT * FROM orders WHERE id=? AND buyer_id=?'+suffix,(order_id,user['id'])).fetchone()
            if not order:raise HTTPException(404,'Nie znaleziono zamówienia')
            if order['status']!='odebrane' or order['pin_used']!=1 or not order['confirmed_at']:
                raise HTTPException(409,'Ocenę można wystawić dopiero po potwierdzonym odbiorze zamówienia')
            old=con.execute('SELECT stars FROM seller_ratings WHERE order_id=?',(order_id,)).fetchone()
            if old:
                if old['stars']!=payload.stars:raise HTTPException(409,'To zamówienie zostało już ocenione')
                return {'order_id':order_id,'stars':old['stars'],'already_rated':True}
            con.execute('INSERT INTO seller_ratings(order_id,buyer_id,farmer_id,stars) VALUES(?,?,?,?)',(order_id,user['id'],order['farmer_id'],payload.stars))
            return {'order_id':order_id,'stars':payload.stars,'already_rated':False}
