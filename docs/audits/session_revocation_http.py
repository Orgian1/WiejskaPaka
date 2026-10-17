"""Reproducible HTTP sweep of revoked sessions, all roles and private routes.

Run from the project root with its Python environment. Only temporary SQLite,
loopback Uvicorn and synthetic accounts are used; reports contain no tokens.
This is a denial sweep, not proof of per-resource authorization for live users.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from scripts.run_phone_demo import demo_environment
from scripts.run_tests_per_file import application_fingerprint
from tests.test_purchase_record_http_restart import server,account


def run():
    fingerprint=application_fingerprint(ROOT);rows=[];operations=0
    with tempfile.TemporaryDirectory(prefix='wp_session_sweep_') as folder:
        folder=Path(folder)
        safe_env=demo_environment(os.environ,folder/'inventory.sqlite3')
        os.environ.clear();os.environ.update(safe_env)
        from scripts.audit_route_auth_dependencies import audit,is_public
        from scripts.audit_anonymous_http_routes import resolved_path
        routes=[r for r in audit()['routes'] if not is_public(r['method'],r['path'])]
        database=folder/'http.sqlite3'
        with server(database) as client:
            for role in ('klient','rolnik','dostawca','admin'):
                for scenario in ('logout','logout_all','logout_others','password_change','expired'):
                    actor=account(client,'klient' if role=='admin' else role)
                    me=client.get('/auth/me',headers=actor);operations+=1
                    assert me.status_code==200
                    if role=='admin':
                        with sqlite3.connect(database) as con:con.execute('UPDATE users SET role=? WHERE id=?',('admin',me.json()['id']))
                    if scenario=='logout':
                        assert client.post('/auth/logout',headers=actor).status_code==200;operations+=1
                    elif scenario=='logout_all':
                        assert client.post('/auth/logout-all',headers=actor).status_code==200;operations+=1
                    elif scenario=='logout_others':
                        logged=client.post('/auth/login',json={'email':me.json()['email'],'password':'Disposable-private-record-123!'});operations+=1
                        assert logged.status_code==200
                        current={'Authorization':'Bearer '+logged.json()['access_token']}
                        assert client.post('/auth/logout-others',headers=current).status_code==200;operations+=1
                        assert client.get('/auth/me',headers=current).status_code==200;operations+=1
                    elif scenario=='password_change':
                        changed=client.post('/auth/change-password',headers=actor,json={'current_password':'Disposable-private-record-123!','new_password':'New-private-denial-sweep-password!'});operations+=1
                        assert changed.status_code==200
                    else:
                        with sqlite3.connect(database) as con:con.execute('UPDATE sessions SET expires_at=? WHERE user_id=?',('2000-01-01T00:00:00Z',me.json()['id']))
                    for route in routes:
                        response=client.request(route['method'],resolved_path(route['path']),headers=actor,
                            json={} if route['method'] in ('POST','PUT','PATCH') else None)
                        rows.append({'role':role,'scenario':scenario,'method':route['method'],'path':route['path'],
                                     'status':response.status_code,'no_store':response.headers.get('cache-control')=='no-store'})
    assert application_fingerprint(ROOT)==fingerprint
    failures=[r for r in rows if r['status']!=401 or not r['no_store']]
    return {'status':'PASS' if not failures else 'FAIL','timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'application_sha256':fingerprint,'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'private_routes':len(routes),'roles':4,'scenarios_per_role':5,'denial_requests':len(rows),
        'auxiliary_http_requests':operations,'synthetic_account_register_login_requests':40,
        'checks_count':len(rows)*2,'failures':failures,'results':rows,
        'scope':'Real TCP HTTP, disposable SQLite; revoked/expired tokens on all private routes. 401 and no-store required; no claim of live-owner resource authorization.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',required=True);args=parser.parse_args()
    result=run();Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False,indent=2))
    sys.exit(0 if result['status']=='PASS' else 1)
