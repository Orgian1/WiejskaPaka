"""Synthetic four-role setup must never reuse a database or external secrets."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest
from backend.payment_integrity import audit_payment_integrity
from tests.test_purchase_record_http_restart import server

ROOT=Path(__file__).resolve().parents[1]


def prepare_sample(directory,env=None):
    result=subprocess.run([sys.executable,'-m','scripts.prepare_sample_demo','--directory',str(directory)],
        cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
    assert result.returncode==0,'Sample setup failed (private output withheld)'
    return json.loads(result.stdout)


def test_setup_is_independent_private_and_source_configuration_untouched(tmp_path):
    source=tmp_path/'original.sqlite3';source.write_bytes(b'existing private source')
    key=tmp_path/'original-key';key.write_bytes(b'existing private key')
    env={**os.environ,'WIEJSKAPAKA_DB':str(source),'DATABASE_URL':'postgresql://not-real.invalid/production',
        'WP_CHECKOUT_KEY_FILE':str(key),'WP_TEST_RESET_OUTBOX':str(tmp_path/'foreign-mailbox'),
        'WP_ENV':'production','NEON_DATABASE_URL':'postgresql://not-real.invalid/neon'}
    directory=tmp_path/'sample'
    result=prepare_sample(directory,env)
    assert result['summary']=={'users':4,'products':2,'shipments':2,'orders':4,'payments_checked':4,'delivery_grosze':501}
    assert source.read_bytes()==b'existing private source' and key.read_bytes()==b'existing private key'
    assert not (tmp_path/'foreign-mailbox').exists()
    assert set(result['credentials'])=={'klient','rolnik','dostawca','admin'}
    assert len({c['password'] for c in result['credentials'].values()})==4
    database=Path(result['database'])
    with closing(sqlite3.connect(database)) as con:
        con.row_factory=sqlite3.Row
        assert con.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]==0
        assert audit_payment_integrity(con)=={'checked_payments':4,'issues':[],'ok':True}
        assert sorted(row[0] for row in con.execute('SELECT stock FROM products'))==[28,28]
        assert con.execute('SELECT SUM(delivery_grosze) FROM orders').fetchone()[0]==501
        for account in result['credentials'].values():
            assert account['password'].encode() not in database.read_bytes()
    if os.name=='posix':
        assert directory.stat().st_mode & 0o077==0
        assert database.stat().st_mode & 0o077==0
    before=database.read_bytes()
    refused=subprocess.run([sys.executable,'-m','scripts.prepare_sample_demo','--directory',str(directory)],
        cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert refused.returncode==1 and not refused.stdout
    assert database.read_bytes()==before
    assert str(directory) not in refused.stderr


@pytest.mark.parametrize('existing',['directory','file'])
def test_setup_refuses_every_existing_target(tmp_path,existing):
    target=tmp_path/'existing'
    if existing=='directory':target.mkdir();(target/'keep').write_bytes(b'untouched')
    else:target.write_bytes(b'untouched')
    result=subprocess.run([sys.executable,'-m','scripts.prepare_sample_demo','--directory',str(target)],
        cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==1 and not result.stdout
    assert (target/'keep' if existing=='directory' else target).read_bytes()==b'untouched'


def test_imported_application_cannot_seed_any_second_database(tmp_path):
    code="import sys; from scripts.prepare_sample_demo import main; sys.modules['backend.app']=object(); raise SystemExit(main(['--directory',sys.argv[1]]))"
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path/'blocked')],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==1 and not (tmp_path/'blocked').exists()


def test_ready_sample_supports_receipt_delivery_and_admin_review_over_real_http(tmp_path):
    result=prepare_sample(tmp_path/'sample')
    headers={}
    with server(Path(result['database'])) as client:
        for role,credentials in result['credentials'].items():
            response=client.post('/auth/login',json=credentials);assert response.status_code==200
            headers[role]={'Authorization':'Bearer '+response.json()['access_token']}
            assert client.get('/auth/me',headers=headers[role]).json()['role']==role
        assert client.post('/auth/register',json={'email':'forbidden-admin@example.invalid','password':'Private-example-123!','role':'admin'}).status_code==422
        shipments=client.get('/shipments/mine',headers=headers['klient']).json()['shipments']
        assert len(shipments)==2
        for shipment in shipments:
            sid=shipment['id']
            response=client.post(f'/shipments/{sid}/recover-pin-test',headers=headers['klient'],
                json={'password':result['credentials']['klient']['password']})
            assert response.status_code==200
            actor='rolnik' if shipment['fulfillment']=='odbior' else 'dostawca'
            response=client.post(f'/shipments/{sid}/confirm',headers=headers[actor],
                json={'pin':response.json()['pin_test_only'],'checked_goods':True})
            assert response.status_code==200 and response.json()['confirmed']
        assert client.get('/couriers/me/active-addresses',headers=headers['dostawca']).json()==[]
        status=client.get('/farmers/me/compliance',headers=headers['rolnik']).json()
        assert status['completed_transaction_count']==2
        queue=client.get('/admin/farmers/compliance-queue?status=pending',headers=headers['admin']).json()
        profile=queue['profiles'][0]
        response=client.post(f'/admin/farmers/{profile["farmer_id"]}/compliance/review',headers=headers['admin'],json={
            'decision':'approved','reason':'Odbiór syntetycznego demo',
            'expected_rules_version':profile['rules_version'],'expected_review_status':profile['review_status'],'expected_reviewed_at':profile['reviewed_at']})
        assert response.status_code==200 and not response.json()['can_receive_real_payouts']


def test_partial_preparation_failure_removes_only_its_new_directory(tmp_path):
    kept=tmp_path/'keep';kept.write_text('unchanged')
    code="""import sys
import fastapi.testclient
def unavailable(*args,**kwargs):raise RuntimeError('private failure')
fastapi.testclient.TestClient=unavailable
from scripts.prepare_sample_demo import main
raise SystemExit(main(['--directory',sys.argv[1]]))
"""
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path/'partial')],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==1 and not result.stdout
    assert not (tmp_path/'partial').exists() and kept.read_text()=='unchanged'
    assert 'private failure' not in result.stderr
