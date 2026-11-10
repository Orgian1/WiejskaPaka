"""Real loopback HTTP: discover -> point policy -> checkout -> PIN/refund.

Uses only disposable SQLite and synthetic data. No location history, geocoding,
GitHub, production payments or remote database. No Chromium evidence implied.
"""
from contextlib import closing
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from scripts.run_phone_demo import demo_environment
from run_tests_per_file import application_fingerprint


def run():
    source=application_fingerprint(ROOT);checks=[];requests=0
    def check(condition,label):
        if not condition:raise AssertionError(label)
        checks.append(label)
    with tempfile.TemporaryDirectory(prefix='wp_local_market_http_') as folder:
        database=Path(folder)/'market.sqlite3';env=demo_environment(os.environ,database)
        env['WP_ENABLE_TEST_PAYMENTS']='1'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        with tempfile.TemporaryFile() as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=log,stderr=log)
            try:
                with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=15,trust_env=False) as client:
                    for _ in range(100):
                        if process.poll() is not None:raise RuntimeError('Disposable HTTP API failed to start')
                        try:
                            if client.get('/health').status_code==200:break
                        except httpx.TransportError:pass
                        time.sleep(.1)
                    else:raise TimeoutError('Disposable HTTP startup')
                    def request(method,path,headers=None,body=None,expected=200):
                        nonlocal requests
                        r=client.request(method,path,headers=headers,json=body);requests+=1
                        check(r.status_code==expected,f'{method} {path} -> {expected}')
                        check(r.headers.get('x-content-type-options')=='nosniff','security response header')
                        if method!='GET':check(r.headers.get('cache-control')=='no-store','private query/write is not cached')
                        return r.json()
                    def account(role):
                        email=uuid4().hex+'@example.invalid';password='Synthetic-local-market-123!'
                        uid=request('POST','/auth/register',body={'email':email,'password':password,'role':role},expected=201)['id']
                        token=request('POST','/auth/login',body={'email':email,'password':password})['access_token']
                        return {'Authorization':'Bearer '+token},uid
                    farmer,fid=account('rolnik');buyer,_=account('klient');other,_=account('rolnik');courier,cid=account('dostawca')
                    products=[]
                    for price,fee in [(199,501),(301,399)]:
                        products.append(request('POST','/products',farmer,{'name':'ŁĄKOWE ziemniaki','price_grosze':price,'delivery_grosze':fee,'stock':10},201)['id'])
                    body={'name':'Punkt lokalnego testu','city':'Opole','street':'Polna 1','opening_hours':'9:00–17:00','latitude_e6':52_000_000,'longitude_e6':16_000_000}
                    point=request('POST','/pickup-points',farmer,body,201)['id']
                    query={'latitude_e6':52_000_000,'longitude_e6':16_000_000,'q':'lakowe ziemniaki'}
                    for radius in (100,500,1000,5000):
                        result=request('POST','/marketplace/nearby',body={**query,'radius_m':radius})
                        check({o['product']['id'] for o in result['items']}==set(products),'all requested radii discover both products')
                        check(all(o['distance_m']==0 and o['pickup_point']['id']==point for o in result['items']),'point and distance match')
                        check(all(type(o['product']['price_grosze']) is int for o in result['items']),'price remains integer grosze')
                        check(all(s not in json.dumps(result) for s in ('password_hash','pin_hash','token_hash','phone','@example','latitude_e6')),'public result excludes account and customer location data')
                    request('PUT',f'/pickup-points/{point}',other,{**body,'active':False},404)
                    request('PUT',f'/pickup-points/{point}',buyer,{**body,'active':False},403)
                    order=request('POST','/orders',buyer,{'product_id':products[0],'quantity':1,'fulfillment':'odbior','pickup_point_id':point},201)
                    request('PUT',f'/pickup-points/{point}',farmer,{**body,'street':'Inna 99','active':True},409)
                    request('PUT',f'/pickup-points/{point}',farmer,{**body,'active':False})
                    check(request('POST','/marketplace/nearby',body={**query,'radius_m':1000})['items']==[],'inactive point not discoverable')
                    request('POST','/orders',buyer,{'product_id':products[0],'quantity':1,'fulfillment':'odbior','pickup_point_id':point},422)
                    request('POST',f'/test/payments/{order["id"]}/events',buyer,{'event_id':uuid4().hex,'event_type':'payment_success_test'})
                    request('POST',f'/test/orders/{order["id"]}/ready',farmer)
                    confirmation=request('POST',f'/orders/{order["id"]}/confirm',farmer,{'pin':order['pin_test_only'],'checked_goods':True})
                    check(confirmation['confirmed'],'existing order can be collected after point deactivation')
                    request('PUT',f'/pickup-points/{point}',farmer,{**body,'active':True})
                    # A discovered two-product cart still has one delivery fee and full courier-fault refund.
                    for pid in products:request('PUT','/cart/items',buyer,{'product_id':pid,'quantity':1})
                    shipment=request('POST','/cart/checkout-test',buyer,{'fulfillment':'dostawa','delivery_city':'Opole','delivery_street':'Testowa 2','delivery_postal_code':'45-001'},201)
                    check(shipment['delivery_grosze']==501 and shipment['total_grosze']==1001,'one fee for both cart lines: 199+301+501 grosze')
                    for item in shipment['orders']:request('POST',f'/test/payments/{item["id"]}/events',buyer,{'event_id':uuid4().hex,'event_type':'payment_success_test'})
                    sid=shipment['shipment_id']
                    request('POST',f'/shipments/{sid}/assign-courier-test',farmer,{'courier_id':cid})
                    request('POST',f'/shipments/{sid}/dispatch-test',farmer)
                    refund=request('POST',f'/shipments/{sid}/courier-failure-test',farmer,{'reason':'dostawca_nie_przyjechal'})
                    check(refund['refund_grosze']==1001,'100 percent of payment including single delivery fee refunded')
                    check(request('GET','/couriers/me/active-addresses',courier)==[],'delivery address access revoked after refund')
                    with closing(sqlite3.connect(database)) as con, con:
                        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                        check(not any('customer_location' in n or 'search_history' in n for n in tables),'no customer location/history table')
                        check(con.execute('PRAGMA foreign_key_check').fetchall()==[],'foreign keys remain valid')
                        check(con.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite integrity')
                    home=client.get('/');check('geolocation=(self)' in home.headers['permissions-policy'],'device location restricted to self')
                    asset=client.get('/assets/nearby.js');check(asset.status_code==200 and 'function searchNearby' in asset.text,'new interface asset is served')
            finally:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    check(source==application_fingerprint(ROOT),'application unchanged during real HTTP gate')
    return {'status':'PASS','application_sha256':source,'http_requests':requests,'checks_count':len(checks),'checks':checks,
            'scope':'real loopback HTTP, disposable SQLite, synthetic location/accounts, simulated payments',
            'timestamp_utc':datetime.now(timezone.utc).isoformat()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',default='audit_local_marketplace_http.json');args=parser.parse_args()
    result=run();Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2))
