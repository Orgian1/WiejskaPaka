"""Real PostgreSQL: capabilities, RLS, SQL credential compromise and rollback.

No external DSN: every test module creates its own disposable local cluster.
"""
import hashlib
import hmac
import json
import secrets
from pathlib import Path
import time
import pytest
pgserver=pytest.importorskip('pgserver')
psycopg=pytest.importorskip('psycopg')
from psycopg.rows import dict_row
from backend.pg_adapter import PgConnection
from backend.rls_gateway import database_context
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def secured(tmp_path_factory):
    directory=tmp_path_factory.mktemp('capability-rls')
    server=pgserver.get_server(directory/'data')
    uri=server.get_uri('wp_test_capabilities')
    key=secrets.token_bytes(32);path=directory/'key.json'
    path.write_text(json.dumps({'key':key.hex()}));path.chmod(0o600)
    env=pytest.MonkeyPatch();env.setenv('WP_RLS_KEY_FILE',str(path));env.setenv('WP_RLS_GATEWAY','1')
    from database.verify_test_migrations import verify
    from database.rls_test_setup import provision
    tokens={uid:secrets.token_urlsafe(32) for uid in range(1,8)}
    with psycopg.connect(server.get_uri(),autocommit=True) as admin:
        admin.execute('CREATE DATABASE wp_test_capabilities')
    with psycopg.connect(uri,autocommit=True) as admin:
        for f in verify(ROOT/'database')['files']:admin.execute((ROOT/'database'/f['file']).read_text())
        with pytest.raises(psycopg.Error,match='compatibility approval'):
            admin.execute((ROOT/'database/security_rls/001_gateway.up.sql').read_text())
        admin.execute('ROLLBACK')
        admin.execute('CREATE ROLE cap_login LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE')
        for uid,role in [(1,'klient'),(2,'klient'),(3,'rolnik'),(4,'rolnik'),(5,'dostawca'),(6,'dostawca'),(7,'admin')]:
            admin.execute('INSERT INTO users(id,email,password_hash,role) VALUES (%s,%s,%s,%s)',(uid,f'{uid}@test.invalid','private-password-hash',role))
            admin.execute("INSERT INTO sessions VALUES (%s,%s,'2099-01-01T00:00:00Z')",(hashlib.sha256(tokens[uid].encode()).hexdigest(),uid))
        for oid,buyer,seller in [(1,1,3),(2,2,4)]:
            admin.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES(%s,%s,'Test',100,100,10)",(oid,seller))
            admin.execute("INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at) VALUES(%s,%s,%s,%s,1,100,100,200,'dostawa','w_drodze_testowo',%s,'private-pin-hash','2026-11-15')",(oid,buyer,seller,oid,f'CODE-{oid}'))
            admin.execute("INSERT INTO order_locations VALUES(%s,NULL,'Private city','Private street','00-001')",(oid,))
        admin.execute("INSERT INTO delivery_assignments VALUES(1,5,3,'2026-11-15')")
        admin.execute('INSERT INTO wallet_preview_accounts(user_id,available_grosze) VALUES(1,100),(2,200)')
        provision(admin,key,'cap_login')
        admin.execute('CREATE ROLE cap_backup LOGIN IN ROLE wp_rls_backup')
    yield uri,key,tokens
    with psycopg.connect(uri,autocommit=True) as admin:
        admin.execute((ROOT/'database/security_rls/001_gateway.down.sql').read_text())
        assert admin.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='public.orders'::regclass").fetchone()==(False,False)
        admin.execute('DROP ROLE cap_login')
        admin.execute('DROP ROLE cap_backup')
    env.undo();server.cleanup()

@pytest.fixture
def raw(secured):
    with psycopg.connect(secured[0],user='cap_login',row_factory=dict_row) as connection:
        try:yield connection
        finally:connection.rollback()

@pytest.mark.parametrize('sql',[
 'SELECT * FROM orders','SELECT pin_hash FROM orders','SELECT * FROM order_locations',
 'SELECT password_hash FROM users','SELECT token_hash FROM sessions','SELECT * FROM wallet_preview_accounts',
 'SELECT key FROM wp_rls_keys.secrets','INSERT INTO wp_rls.context VALUES(1,1,1,\'admin\',\'maintenance\',\'x\')',
 'UPDATE wallet_preview_accounts SET available_grosze=999999','UPDATE users SET role=\'admin\'',
 'DELETE FROM orders','ALTER TABLE orders DISABLE ROW LEVEL SECURITY',
 'SET ROLE wp_rls_guard','SET ROLE wp_rls_executor','SET ROLE wp_rls_backup',
])
def test_sql_login_cannot_read_write_or_escalate(raw,sql):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):raw.execute(sql)

@pytest.mark.parametrize('signature',[None,'','0'*64,'z'*64])
def test_unsigned_capabilities_are_rejected_even_for_maintenance(raw,signature):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):raw.execute('SELECT wp_rls.execute(%s,%s)',('{}',signature))

@pytest.mark.parametrize('actor,ids',[(1,[1]),(2,[2]),(3,[1]),(4,[2]),(5,[1]),(6,[]),(7,[1,2])])
def test_signed_queries_still_obey_account_row_isolation(raw,secured,actor,ids):
    with database_context('request','Bearer '+secured[2][actor]):
        rows=PgConnection(raw).execute('SELECT id FROM orders ORDER BY id').fetchall()
    assert [r['id'] for r in rows]==ids


def test_actor_and_role_gucs_do_not_change_the_verified_actor(raw,secured):
    raw.execute("SELECT set_config('wiejskapaka.actor_id','2',true),set_config('wiejskapaka.role','admin',true),set_config('wp_rls.purpose','maintenance',true)")
    with database_context('request','Bearer '+secured[2][1]):
        assert PgConnection(raw).execute('SELECT id FROM orders ORDER BY id').fetchall()==[{'id':1}]
        assert PgConnection(raw).execute('SELECT user_id FROM wallet_preview_accounts').fetchall()==[{'user_id':1}]


def test_signed_but_cross_account_writes_are_rejected(raw,secured):
    with database_context('request','Bearer '+secured[2][1]):
        c=PgConnection(raw)
        assert c.execute('UPDATE wallet_preview_accounts SET available_grosze=99999 WHERE user_id=2').rowcount==0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):c.execute('UPDATE orders SET buyer_id=2 WHERE id=1')


def capability(raw,secured,**changes):
    p=raw.execute('SELECT pg_backend_pid() AS pid,txid_current() AS xid,current_database() AS db').fetchone()
    p.update(nonce=secrets.token_hex(24),expires=int(time.time())+60,scope='request',bearer=secured[2][1],sql='SELECT id FROM orders ORDER BY id',columns=[['id',20]])
    p.update(changes)
    payload=json.dumps(p,separators=(',',':'));mac=hmac.new(secured[1],payload.encode(),hashlib.sha256).hexdigest()
    return payload,mac

@pytest.mark.parametrize('change',[{'pid':0},{'xid':0},{'db':'different'},{'expires':0}])
def test_signed_context_is_bound_to_database_pid_transaction_and_expiry(raw,secured,change):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):raw.execute('SELECT wp_rls.execute(%s,%s)',capability(raw,secured,**change))


def test_modification_of_sql_or_scope_invalidates_signature(raw,secured):
    payload,mac=capability(raw,secured)
    forged=json.loads(payload);forged.update(sql='UPDATE users SET role=\'admin\'',scope='maintenance')
    with pytest.raises(psycopg.errors.InsufficientPrivilege):raw.execute('SELECT wp_rls.execute(%s,%s)',(json.dumps(forged,separators=(',',':')),mac))


def test_successful_capability_is_not_replayable_in_another_transaction(raw,secured):
    proof=capability(raw,secured)
    assert raw.execute('SELECT wp_rls.execute(%s,%s) AS result',proof).fetchone()['result']['rows']==[['1']]
    raw.commit()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):raw.execute('SELECT wp_rls.execute(%s,%s)',proof)


def test_cleanup_and_native_types_preserve_money_and_binary(raw,secured):
    from decimal import Decimal
    c=PgConnection(raw)
    with database_context('request','Bearer '+secured[2][1]):
        row=c.execute('SELECT ?::bytea AS secret,?::numeric AS amount,true AS ok',(b'\x00\xff','12345678901234567890.12345')).fetchone()
    assert row=={'secret':b'\x00\xff','amount':Decimal('12345678901234567890.12345'),'ok':True}
    with database_context('request',None):assert c.execute('SELECT id FROM orders').fetchall()==[]
    with psycopg.connect(secured[0]) as admin:
        assert admin.execute('SELECT count(*) FROM wp_rls.context').fetchone()==(0,)
        flags=admin.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r'").fetchall()
        assert flags and all(x==(True,True) for x in flags)


def test_readonly_diagnostics_use_signed_context_without_writes(raw,secured):
    raw.execute('SET TRANSACTION READ ONLY')
    with database_context('request','Bearer '+secured[2][1]):
        c=PgConnection(raw)
        assert c.execute('SELECT id FROM orders').fetchall()==[{'id':1}]
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):c.execute('UPDATE wallet_preview_accounts SET available_grosze=999 WHERE user_id=1')
    raw.rollback()
    assert raw.execute("SELECT current_setting('wp_rls.read_proof',true) AS proof").fetchone()['proof'] in (None,'')


def test_replay_in_same_transaction_is_rejected(raw,secured):
    proof=capability(raw,secured)
    raw.execute('SELECT wp_rls.execute(%s,%s)',proof)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):raw.execute('SELECT wp_rls.execute(%s,%s)',proof)


@pytest.mark.parametrize('token_kind',['unknown','stored-hash','expired','revoked'])
def test_no_identity_from_unknown_hash_expired_or_revoked_bearers(raw,secured,token_kind):
    token=secrets.token_urlsafe(32)
    if token_kind=='stored-hash':token=hashlib.sha256(secured[2][1].encode()).hexdigest()
    if token_kind in ('expired','revoked'):
        digest=hashlib.sha256(token.encode()).hexdigest()
        with psycopg.connect(secured[0],autocommit=True) as admin:
            admin.execute('INSERT INTO sessions VALUES (%s,1,%s)',(digest,'2000-01-01T00:00:00Z' if token_kind=='expired' else '2099-01-01T00:00:00Z'))
            if token_kind=='revoked':admin.execute('DELETE FROM sessions WHERE token_hash=%s',(digest,))
    with database_context('request','Bearer '+token):assert PgConnection(raw).execute('SELECT id FROM orders').fetchall()==[]


def test_address_is_revoked_after_delivery_even_for_a_signed_query(raw,secured):
    with database_context('request','Bearer '+secured[2][5]):
        assert len(PgConnection(raw).execute('SELECT delivery_street FROM order_locations').fetchall())==1
        with psycopg.connect(secured[0],autocommit=True) as admin:
            admin.execute("UPDATE orders SET status='odebrane',pin_used=1,confirmed_at='2026-11-15' WHERE id=1")
        try:assert PgConnection(raw).execute('SELECT delivery_street FROM order_locations').fetchall()==[]
        finally:
            with psycopg.connect(secured[0],autocommit=True) as admin:
                admin.execute("UPDATE orders SET status='w_drodze_testowo',pin_used=0,confirmed_at=NULL WHERE id=1")



def test_backup_role_can_read_snapshot_but_not_signing_key_or_write(secured):
    with psycopg.connect(secured[0],user='cap_backup') as con:
        assert con.execute('SELECT id FROM orders ORDER BY id').fetchall()==[(1,),(2,)]
        for query in ('SELECT key FROM wp_rls_keys.secrets','UPDATE orders SET buyer_id=2',"SELECT wp_rls.execute('{}',NULL)"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with con.transaction():con.execute(query)



def test_runtime_preflight_rejects_private_function_role_membership(raw,secured):
    from backend.postgres_runtime_role import assert_runtime_role
    assert_runtime_role(raw)
    with psycopg.connect(secured[0],autocommit=True) as admin:admin.execute('GRANT wp_rls_guard TO cap_login')
    try:
        with pytest.raises(RuntimeError):assert_runtime_role(raw)
    finally:
        with psycopg.connect(secured[0],autocommit=True) as admin:admin.execute('REVOKE wp_rls_guard FROM cap_login')



def test_rollback_refuses_to_disable_new_unreviewed_policies(secured):
    with psycopg.connect(secured[0],autocommit=True) as admin:
        admin.execute('CREATE POLICY later_security_review ON public.orders FOR SELECT TO cap_login USING(false)')
        try:
            with pytest.raises(psycopg.Error,match='rollback review'):
                admin.execute((ROOT/'database/security_rls/001_gateway.down.sql').read_text())
            admin.execute('ROLLBACK')
            assert admin.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='public.orders'::regclass").fetchone()==(True,True)
        finally:admin.execute('DROP POLICY later_security_review ON public.orders')
