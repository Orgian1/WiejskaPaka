"""SQLite search scale/reference gate; synthetic points, independent haversine oracle.

SQL timings are observations for this machine, not a production capacity claim.
"""
import argparse
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import random
import sqlite3
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from backend.local_marketplace import SCHEMA_SQLITE,EARTH_RADIUS_M,index_product,save_coordinates,nearby_offers
from run_tests_per_file import application_fingerprint


def run(points=10000,queries=40):
    source=application_fingerprint(ROOT);rng=random.Random(112801)
    con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row;con.execute('PRAGMA foreign_keys=ON')
    con.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY,role TEXT);
        CREATE TABLE products(id INTEGER PRIMARY KEY,farmer_id INTEGER REFERENCES users(id),name TEXT,price_grosze INTEGER,delivery_grosze INTEGER,stock INTEGER);
        CREATE TABLE pickup_points(id INTEGER PRIMARY KEY,farmer_id INTEGER REFERENCES users(id),name TEXT,city TEXT,street TEXT,opening_hours TEXT,active INTEGER);
        INSERT INTO users VALUES(1,'rolnik');
        INSERT INTO products VALUES(1,1,'Żółte ziemniaki',199,501,100);
        '''+SCHEMA_SQLITE)
    index_product(con,1,'Żółte ziemniaki');fixtures=[]
    for point in range(1,points+1):
        lat=52_000_000+rng.randint(-150_000,150_000);lon=16_000_000+rng.randint(-250_000,250_000)
        active=point%7!=0
        con.execute('INSERT INTO pickup_points VALUES(?,1,?,?,?,?,?)',(point,'Punkt '+str(point),'Opole','Testowa 1','9-17',int(active)))
        save_coordinates(con,point,lat,lon);fixtures.append((point,math.radians(lat/1e6),math.radians(lon/1e6),active))
    timings=[];invariants=0;reference_distances=0
    try:
        for attempt in range(queries):
            lat_e6=52_000_000+rng.randint(-50_000,50_000);lon_e6=16_000_000+rng.randint(-100_000,100_000)
            radius=(100,500,1000,5000)[attempt%4];lat=math.radians(lat_e6/1e6);lon=math.radians(lon_e6/1e6)
            expected=[]
            for point,plat,plon,active in fixtures:
                if not active:continue
                h=math.sin((plat-lat)/2)**2+math.cos(lat)*math.cos(plat)*math.sin((plon-lon)/2)**2
                distance=2*EARTH_RADIUS_M*math.atan2(math.sqrt(h),math.sqrt(1-h));reference_distances+=1
                if distance<=radius:expected.append((distance,point))
            expected.sort()
            started=time.perf_counter()
            result=nearby_offers(con,latitude_e6=lat_e6,longitude_e6=lon_e6,radius_m=radius,q='zolte ziemniaki',limit=24)
            timings.append((time.perf_counter()-started)*1000)
            assert [r['pickup_point']['id'] for r in result['items']]==[point for _,point in expected[:24]]
            assert result['has_more']==(len(expected)>24);invariants+=2
            for item,(distance,point) in zip(result['items'],expected):
                assert abs(item['distance_m']-math.ceil(distance))<=1
                assert item['product']['price_grosze']==199 and type(item['product']['price_grosze']) is int
                invariants+=2
        assert source==application_fingerprint(ROOT)
        return {'status':'PASS','application_sha256':source,'scope':'in-memory SQLite, synthetic points, independent haversine reference; not PostgreSQL or HTTP',
            'points':points,'queries':queries,'reference_distances':reference_distances,'invariant_checks':invariants,
            'query_ms_observed':{'min':round(min(timings),3),'median':round(sorted(timings)[len(timings)//2],3),'max':round(max(timings),3)},
            'timestamp_utc':datetime.now(timezone.utc).isoformat()}
    finally:con.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',default='audit_local_search_scale.json');args=parser.parse_args()
    result=run();Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
