"""Cross-account IDOR audit via real loopback HTTP and disposable SQLite."""
import json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.run_phone_demo import demo_environment

def run():
    checks=[]
    with tempfile.TemporaryDirectory(prefix='wp_idor_http_') as tmp:
        with socket.socket() as s:
            s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
        env=demo_environment(os.environ,Path(tmp)/'idor.sqlite3')
        proc=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=7,trust_env=False) as c:
                for _ in range(100):
                    if proc.poll() is not None: raise RuntimeError(proc.communicate()[1].decode()[-1000:])
                    try:
                        if c.get('/health').status_code==200: break
                    except httpx.TransportError: pass
                    time.sleep(.1)
                else: raise TimeoutError('HTTP startup')
                def request(label,method,path,allowed,auth=None,body=None):
                    r=c.request(method,path,headers=auth,json=body)
                    assert r.status_code in allowed,(label,r.status_code,r.text[:300])
                    checks.append({'check':label,'http':r.status_code})
                    return r.json()
                headers={}
                for who,role in [('buyer','klient'),('other_buyer','klient'),('farmer','rolnik'),('other_farmer','rolnik'),('courier','dostawca'),('other_courier','dostawca')]:
                    email=f'idor-{who}@example.invalid'; password='TestoweHaslo_123456789'
                    request('register '+who,'POST','/auth/register',{201},body={'email':email,'password':password,'role':role})
                    token=request('login '+who,'POST','/auth/login',{200},body={'email':email,'password':password})['access_token']
                    headers[who]={'Authorization':'Bearer '+token}
                product=request('create product','POST','/products',{201},headers['farmer'],{'name':'Jablka IDOR','price_grosze':349,'delivery_grosze':501,'stock':12})
                order=request('create order','POST','/orders',{201},headers['buyer'],{'product_id':product['id'],'quantity':2,'fulfillment':'dostawa','delivery_city':'Radom','delivery_street':'Sekretna 7','delivery_postal_code':'26-600'})
                oid=order['id']
                for who in ('other_buyer','other_farmer','courier','other_courier'):
                    request(who+' denied order events','GET',f'/orders/{oid}/events',{403,404},headers[who])
                    request(who+' denied location','GET',f'/orders/{oid}/location',{403,404},headers[who])
                    request(who+' denied order confirmation','POST',f'/orders/{oid}/confirm',{403,404},headers[who],{'pin':'000000','checked_goods':True})
                for who in ('other_buyer','other_farmer','courier','other_courier'):
                    request(who+' denied settlement preview','GET',f'/marketplace/orders/{oid}/settlement-preview',{403,404},headers[who])
                request('owner farmer settlement preview','GET',f'/marketplace/orders/{oid}/settlement-preview',{200},headers['farmer'])
                for who in ('other_buyer','other_farmer','courier','other_courier'):
                    request(who+' denied dispatch','POST',f'/orders/{oid}/dispatch-test',{403,404},headers[who])
                request('owner buyer events','GET',f'/orders/{oid}/events',{200},headers['buyer'])
                request('owner farmer events','GET',f'/orders/{oid}/events',{200},headers['farmer'])
                for who in ('other_buyer','other_farmer'):
                    rows=request(who+' list orders','GET','/orders/me',{200},headers[who]); assert all(x['id']!=oid for x in rows)
                # Privacy contract: public and own-order JSON must not expose phone fields.
                def assert_no_phone_fields(label, payload):
                    forbidden = {'phone', 'phone_number', 'telephone', 'mobile', 'telefon', 'numer_telefonu', 'tel'}
                    def walk(obj, path='$'):
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                assert key.lower() not in forbidden, (label, path, key)
                                walk(value, path + '.' + key)
                        elif isinstance(obj, list):
                            for idx, value in enumerate(obj): walk(value, f'{path}[{idx}]')
                    walk(payload)
                    checks.append({'check': label + ' no phone fields', 'http': 200})
                for label, path, who in [
                    ('public catalog', '/products', None),
                    ('buyer orders', '/orders/me', 'buyer'),
                    ('other buyer orders', '/orders/me', 'other_buyer'),
                    ('farmer orders', '/orders/me', 'farmer'),
                    ('buyer events', f'/orders/{oid}/events', 'buyer'),
                    ('farmer events', f'/orders/{oid}/events', 'farmer'),
                ]:
                    payload = request(label + ' privacy HTTP', 'GET', path, {200}, headers[who] if who else None)
                    assert_no_phone_fields(label, payload)
                assert order['total_grosze']==1199
                checks.append({'check':'integer grosze and one delivery fee','http':200})
        finally:
            proc.terminate()
            try: proc.communicate(timeout=5)
            except subprocess.TimeoutExpired: proc.kill();proc.communicate()
    return {'status':'PASS','count':len(checks),'checks':checks,'scope':'real loopback HTTP, disposable SQLite, six accounts, no external services'}
if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False,indent=2))
