"""Combined catalog filters with portable distance ordering and bounded pages."""
import math
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,Field,model_validator
from backend import product_categories as categories,product_unit_storage,pickup_dates,address_delivery
from backend.local_marketplace import sphere,search_key,EARTH_RADIUS_M


class CatalogQuery(BaseModel):
    model_config={'extra':'forbid'}
    q:str=Field(default='',max_length=120)
    category_id:str|None=Field(default=None,max_length=40)
    subcategory_id:str|None=Field(default=None,max_length=80)
    available_now:bool=False
    fulfillment:Literal['all','odbior','dostawa']='all'
    sort:Literal['newest','nearest']='newest'
    latitude_e6:int|None=Field(default=None,strict=True,ge=-90000000,le=90000000)
    longitude_e6:int|None=Field(default=None,strict=True,ge=-180000000,le=180000000)
    min_price_grosze:int|None=Field(default=None,strict=True,ge=0,le=9000000000000000000)
    max_price_grosze:int|None=Field(default=None,strict=True,ge=0,le=9000000000000000000)
    farmer_id:int|None=Field(default=None,strict=True,ge=1,le=9000000000000000000)
    limit:int=Field(default=24,ge=1,le=100)
    offset:int=Field(default=0,ge=0,le=10000)

    @model_validator(mode='after')
    def valid(self):
        if self.category_id is not None and self.category_id not in {c['id'] for c in categories.CATEGORIES}:raise ValueError('Nieprawidłowa kategoria')
        if self.subcategory_id is not None and (self.category_id,self.subcategory_id) not in categories.PAIRS:raise ValueError('Nieprawidłowa podkategoria')
        if (self.latitude_e6 is None)!=(self.longitude_e6 is None) or (self.sort=='nearest' and self.latitude_e6 is None):raise ValueError('Najpierw ustaw lokalizację lub użyj GPS')
        if self.min_price_grosze is not None and self.max_price_grosze is not None and self.min_price_grosze>self.max_price_grosze:raise ValueError('Nieprawidłowy zakres cen')
        return self


def search(con,query):
    clauses=['NOT EXISTS(SELECT 1 FROM product_listing_states ls WHERE ls.product_id=p.id AND ls.active=0)'];params=[]
    for field,value in [('category_id',query.category_id),('subcategory_id',query.subcategory_id)]:
        if value is not None:clauses.append("COALESCE(m."+field+",'"+('other' if field=='category_id' else 'other-other')+"')=?");params.append(value)
    if query.farmer_id is not None:clauses.append('p.farmer_id=?');params.append(query.farmer_id)
    if query.q.strip():
        literal=search_key(query.q.strip()).replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        clauses.append("COALESCE(s.name_key,LOWER(p.name)) LIKE ? ESCAPE '\\'");params.append('%'+literal+'%')
    for field,op,value in [('price_grosze','>=',query.min_price_grosze),('price_grosze','<=',query.max_price_grosze)]:
        if value is not None:clauses.append('p.'+field+op+'?');params.append(value)
    pickup="EXISTS(SELECT 1 FROM pickup_points t WHERE t.farmer_id=p.farmer_id AND t.active=1"
    date_clause=''
    if pickup_dates.enabled():date_clause=" AND EXISTS(SELECT 1 FROM pickup_point_dates d WHERE d.point_id=t.id AND d.attendance_date>='"+pickup_dates.today().isoformat()+"')"
    pickup+=date_clause+')'
    delivery='EXISTS(SELECT 1 FROM seller_delivery_windows w WHERE w.farmer_id=p.farmer_id AND w.active=1)' if address_delivery.enabled() else '1=1'
    if query.fulfillment!='all':clauses.append(pickup if query.fulfillment=='odbior' else delivery)
    if query.available_now:clauses+=['p.stock>0','('+pickup+' OR '+delivery+')']
    distance='NULL';prefix=[]
    if query.sort=='nearest':
        x,y,z=sphere(query.latitude_e6,query.longitude_e6)
        distance='''(SELECT MIN((c.sphere_x-?)*(c.sphere_x-?)+(c.sphere_y-?)*(c.sphere_y-?)+(c.sphere_z-?)*(c.sphere_z-?))
          FROM pickup_points t JOIN pickup_point_coordinates c ON c.point_id=t.id WHERE t.farmer_id=p.farmer_id AND t.active=1'''+date_clause+')'
        prefix=[x,x,y,y,z,z]
    source='products p LEFT JOIN product_classifications m ON m.product_id=p.id LEFT JOIN product_search_names s ON s.product_id=p.id'
    where=' AND '.join(clauses)
    total=con.execute('SELECT COUNT(*) AS n FROM '+source+' WHERE '+where,tuple(params)).fetchone()['n']
    ordering='CASE WHEN distance_squared IS NULL THEN 1 ELSE 0 END,distance_squared,id DESC' if query.sort=='nearest' else 'id DESC'
    # Outer query permits alias sorting consistently on SQLite and PostgreSQL.
    rows=con.execute('SELECT * FROM (SELECT p.id,p.farmer_id,p.name,p.price_grosze,p.delivery_grosze,p.stock,'+distance+' AS distance_squared FROM '+source+' WHERE '+where+') catalog_rows ORDER BY '+ordering+' LIMIT ? OFFSET ?',tuple(prefix+params+[query.limit,query.offset])).fetchall()
    items=[]
    for row in rows:
        item=product_unit_storage.enrich_product(con,row);item.update(categories.metadata(con,item['id']));squared=item.pop('distance_squared')
        if query.sort=='nearest':item['distance_m']=None if squared is None else math.ceil(2*EARTH_RADIUS_M*math.asin(min(1,math.sqrt(max(0,squared))/2)))
        items.append(item)
    return {'items':items,'total':total,'limit':query.limit,'offset':query.offset,'distance_reference':'nearest_active_pickup_point' if query.sort=='nearest' else None}


def install(app,db,database_url):
    if not database_url:
        with db() as con:con.executescript('BEGIN IMMEDIATE;\n'+categories.schema_sql()+'\nCOMMIT;')
    @app.get('/product-categories')
    def taxonomy():return {'categories':categories.CATEGORIES}
    @app.post('/catalog/query')
    def catalog(query:CatalogQuery):
        with db() as con:return search(con,query)
