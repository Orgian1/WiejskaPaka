"""Real persisted checkouts; SMTP is injected and never contacts a provider."""
from contextlib import closing
from datetime import datetime, timezone
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from backend import order_mail_outbox as outbox
from backend.checkout_vault import Vault, read_ring
from backend.smtp_reset_transport import outcome
from tests.test_purchase_record_http_restart import server
from tests.test_sqlite_recovery_rehearsal import key_path


@pytest.fixture(scope='module')
def seed(tmp_path_factory):
    database=tmp_path_factory.mktemp('order_mail')/'seed.sqlite3'
    patch=pytest.MonkeyPatch();patch.setenv('WP_ENABLE_PRODUCT_UNITS','1')
    try:
        with server(database) as client:
            actors=[]
            for role in ('rolnik','klient'):
                body={'email':role+'@example.invalid','password':'SyntheticOrderMail2026!','role':role}
                registered=client.post('/auth/register',json=body);assert registered.status_code==201
                token=client.post('/auth/login',json=body).json()['access_token']
                actors.append(({'Authorization':'Bearer '+token},registered.json()['id']))
            (farmer,_),(buyer,buyer_id)=actors
            products=[]
            for price in (349,299):
                r=client.post('/products',headers=farmer,json={'name':'Towar '+str(price),'stock':10,
                    'price_grosze':price,'delivery_grosze':501,'sale_unit':'kg'})
                assert r.status_code==201;products.append(r.json()['id'])
            address={'fulfillment':'dostawa','delivery_city':'Legnica','delivery_street':'Testowa 1','delivery_postal_code':'59-220'}
            direct=client.post('/orders',headers={**buyer,'Idempotency-Key':'mail-direct-0000001'},
                               json={**address,'product_id':products[0],'quantity':1})
            assert direct.status_code==201,direct.text
            for pid in products:assert client.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':1}).status_code==200
            cart=client.post('/cart/checkout-test',headers={**buyer,'Idempotency-Key':'mail-cart-00000001'},json=address)
            assert cart.status_code==201,cart.text
        with closing(sqlite3.connect(database)) as con:con.executescript(outbox.SCHEMA_SQLITE)
        return database,Vault(*read_ring(key_path(database))),buyer_id,direct.json(),cart.json()
    finally:patch.undo()


@pytest.fixture
def store(seed,tmp_path):
    source,vault,buyer_id,direct,cart=seed;path=tmp_path/'outbox.sqlite3'
    with closing(sqlite3.connect(source)) as original,closing(sqlite3.connect(path)) as target:original.backup(target)
    def connect():
        con=sqlite3.connect(path,timeout=10);con.row_factory=sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON');return con
    return connect,vault,buyer_id,direct,cart


def add(store,key='mail-cart-00000001'):
    connect,_,buyer,_,_=store
    with closing(connect()) as con,outbox.transaction(con):
        return outbox.enqueue(con,buyer,key,now=int(datetime.now(timezone.utc).timestamp()))


def state(store):
    with closing(store[0]()) as con:return dict(con.execute('SELECT * FROM order_mail_outbox').fetchone())


def dispatch(store,transport,verified=lambda *args:True,*,shift=0):
    return outbox.dispatch_once(store[0],store[1],transport,verified,
        clock=lambda:int(datetime.now(timezone.utc).timestamp())+shift)


@pytest.mark.parametrize('key',['direct:mail-direct-0000001','mail-cart-00000001'])
def test_one_job_per_purchase_and_durable_start_before_submission(store,key):
    jid=add(store,key);assert add(store,key)==jid;seen=[]
    def transport(recipient,purchase,**kwargs):
        assert state(store)['state']=='started'
        assert recipient=='klient@example.invalid' and kwargs=={'email_verified':True}
        assert purchase.pin==store[3 if key.startswith('direct:') else 4]['pin_test_only' if key.startswith('direct:') else 'shipment_pin_test_only']
        assert purchase.delivery_grosze==501
        assert purchase.total_grosze==(850 if key.startswith('direct:') else 1149)
        assert all(line[2]=='kg' for line in purchase.lines)
        seen.append(purchase.reference);return outcome('ACCEPTED',accepted=True)
    assert dispatch(store,transport)=='ACCEPTED'
    assert dispatch(store,lambda *a,**kw:pytest.fail('Must not resend'))=='IDLE'
    assert len(seen)==1 and state(store)['state']=='accepted'
    ledger=json.dumps(state(store));assert 'klient@example.invalid' not in ledger
    assert 'pin_test_only' not in ledger and 'ciphertext' not in ledger


@pytest.mark.parametrize('problem',['unverified','changed_email','cancelled','expired','bad_vault'])
def test_ineligible_purchase_never_crosses_transport_boundary(store,problem):
    add(store)
    if problem in ('changed_email','cancelled','bad_vault'):
        with closing(store[0]()) as con,outbox.transaction(con):
            if problem=='changed_email':con.execute('UPDATE users SET email=? WHERE id=?',('other@example.invalid',store[2]))
            elif problem=='cancelled':con.execute("UPDATE orders SET status='anulowane_testowo'")
            else:con.execute("UPDATE checkout_idempotency SET response_json='invalid private envelope'")
    result=dispatch(store,lambda *a,**kw:pytest.fail('Private purchase must not be sent'),
                    verified=lambda *a:problem!='unverified',shift=7200 if problem=='expired' else 0)
    assert result=='SKIPPED' and state(store)['state']=='skipped'


@pytest.mark.parametrize('result',[outcome('DELIVERY_UNCERTAIN'),{'status':'private-invalid'},None])
def test_uncertain_or_malformed_result_is_not_retried(store,result):
    add(store)
    assert dispatch(store,lambda *a,**kw:result)=='DELIVERY_UNCERTAIN'
    assert state(store)['state']=='uncertain'
    assert dispatch(store,lambda *a,**kw:pytest.fail('Do not retry'))=='IDLE'


def test_crash_after_start_and_restore_quarantine_cannot_resubmit(store):
    add(store)
    def crash(*args,**kwargs):raise SystemExit('synthetic crash after durable start')
    with pytest.raises(SystemExit):dispatch(store,crash)
    assert state(store)['state']=='started'
    assert dispatch(store,lambda *a,**kw:pytest.fail('Do not retry'),shift=121)=='IDLE'
    assert state(store)['state']=='uncertain'
    with closing(store[0]()) as con,outbox.transaction(con):outbox.quarantine_restored(con)
    assert state(store)['state']=='uncertain'


def test_concurrent_workers_submit_only_once(store):
    add(store);entered=Event();release=Event();seen=[]
    def transport(*args,**kwargs):
        seen.append(1);entered.set();assert release.wait(10);return outcome('ACCEPTED',accepted=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(dispatch,store,transport)
        try:
            assert entered.wait(10)
            assert dispatch(store,lambda *a,**kw:pytest.fail('Second submission'))=='IDLE'
        finally:release.set()
        assert first.result()=='ACCEPTED'
    assert seen==[1]


def test_email_uses_captured_terms_after_product_edit(store):
    add(store)
    with closing(store[0]()) as con,outbox.transaction(con):
        con.execute("UPDATE products SET name='Zmodyfikowana oferta',price_grosze=9999")
    def submit(recipient,purchase,**kwargs):
        assert {line[0] for line in purchase.lines}=={'Towar 349','Towar 299'}
        assert purchase.total_grosze==1149 and purchase.delivery_grosze==501
        return outcome('ACCEPTED',accepted=True)
    assert dispatch(store,submit)=='ACCEPTED'


def test_unknown_purchase_and_cross_buyer_cannot_be_enqueued(store):
    with closing(store[0]()) as con,outbox.transaction(con):
        for buyer,key in [(store[2],'unknown-purchase-00001'),(store[2]+1,'mail-cart-00000001')]:
            with pytest.raises(ValueError,match='ORDER_MAIL_PURCHASE_UNAVAILABLE'):
                outbox.enqueue(con,buyer,key,now=1)
    assert dispatch(store,lambda *a,**kw:pytest.fail('No job'))=='IDLE'


def test_restored_queued_job_is_quarantined_and_enqueue_requires_transaction(store):
    with closing(store[0]()) as con:
        with pytest.raises(ValueError,match='TRANSACTION_REQUIRED'):
            outbox.enqueue(con,store[2],'mail-cart-00000001',now=1)
    add(store)
    with closing(store[0]()) as con,outbox.transaction(con):outbox.quarantine_restored(con)
    assert state(store)['state']=='skipped'
    assert dispatch(store,lambda *a,**kw:pytest.fail('Do not replay backup'))=='IDLE'


@pytest.mark.parametrize('started',[False,True])
def test_actual_snapshot_restore_quarantines_purchase_mail_without_changing_source(store,seed,tmp_path,started):
    from pathlib import Path
    from scripts.sqlite_snapshot import snapshot
    add(store)
    with closing(store[0]()) as con:
        source=Path(con.execute('PRAGMA database_list').fetchone()['file'])
        if started:
            with outbox.transaction(con):con.execute("UPDATE order_mail_outbox SET state='started',started_at=1")
    restored=tmp_path/'restored'
    snapshot(source,key_path(seed[0]),restored,restore=True)
    with closing(sqlite3.connect(restored/'database.sqlite3')) as con:
        assert con.execute("SELECT COUNT(*) FROM order_mail_outbox WHERE state IN ('queued','started')").fetchone()[0]==0
        assert con.execute('SELECT state FROM order_mail_outbox').fetchone()[0]==('uncertain' if started else 'skipped')
        assert con.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]==0
    assert state(store)['state']==('started' if started else 'queued')


@pytest.mark.parametrize('confirmed',[True,False])
def test_real_account_proof_controls_purchase_mail(store,confirmed):
    from backend import email_ownership as proof
    now=int(datetime.now(timezone.utc).timestamp())
    with closing(store[0]()) as con:
        con.executescript(proof.SCHEMA_SQLITE)
        with outbox.transaction(con):
            token=proof.issue(con,store[2],now=now)
            if confirmed:assert proof.consume(con,store[2],token,now=now)
    add(store)
    seen=[]
    def transport(*args,**kwargs):
        seen.append(True)
        return outcome('ACCEPTED',accepted=True)
    assert dispatch(store,transport,verified=proof.verified_recipient)==('ACCEPTED' if confirmed else 'SKIPPED')
    assert len(seen)==int(confirmed)


@pytest.mark.parametrize('confirmed',[False,True])
def test_snapshot_restore_invalidates_account_proofs_and_verification_jobs(store,seed,tmp_path,confirmed):
    from pathlib import Path
    from backend import email_verification_queue as verification, email_ownership as proof
    from backend.reset_mail_queue import KeyRing
    from scripts.sqlite_snapshot import snapshot
    with closing(store[0]()) as con:
        source=Path(con.execute('PRAGMA database_list').fetchone()['file'])
        con.executescript(verification.SCHEMA_SQLITE)
        with outbox.transaction(con):
            verification.enqueue(con,KeyRing({'test':b'q'*32},'test'),store[2],now=100)
            if confirmed:
                row=con.execute('SELECT * FROM email_verification_queue').fetchone()
                token=KeyRing({'test':b'q'*32},'test').decrypt(row).token
                assert proof.consume(con,store[2],token,now=101)
    restored=tmp_path/'verification-restored'
    snapshot(source,key_path(seed[0]),restored,restore=True)
    with closing(sqlite3.connect(restored/'database.sqlite3')) as con:
        assert con.execute('SELECT count(*) FROM account_email_proofs').fetchone()[0]==0
        assert con.execute("SELECT count(*) FROM email_verification_queue WHERE payload IS NOT NULL OR state IN ('queued','started')").fetchone()[0]==0
    with closing(store[0]()) as con:
        assert con.execute('SELECT count(*) FROM account_email_proofs').fetchone()[0]==1
        assert con.execute('SELECT payload FROM email_verification_queue').fetchone()[0] is not None
