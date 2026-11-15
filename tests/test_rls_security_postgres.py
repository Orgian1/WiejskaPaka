"""Execute candidate migrations only in a freshly created local cluster.

Optional test dependency: pgserver (bundled PostgreSQL), never DATABASE_URL.
No inherited connection string or production database is accepted.
"""
import hashlib
from pathlib import Path
import pytest

pgserver = pytest.importorskip('pgserver')
psycopg = pytest.importorskip('psycopg')
ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def cluster(tmp_path_factory):
    server = pgserver.get_server(tmp_path_factory.mktemp('security-pg') / 'data')
    uri = server.get_uri()
    with psycopg.connect(uri, autocommit=True) as admin:
        from database.verify_test_migrations import verify
        reviewed = verify(ROOT / 'database')
        assert reviewed['ok']
        for entry in reviewed['files']:
            admin.execute((ROOT / 'database' / entry['file']).read_text())
        admin.execute("INSERT INTO users(id,email,password_hash,role) VALUES (1,'buyer@test','hash','klient'),(2,'other@test','hash','klient'),(3,'seller@test','hash','rolnik'),(4,'courier@test','hash','dostawca'),(5,'admin@test','hash','admin')")
        for uid in range(1, 6):
            token = f'opaque-test-session-{uid}-not-a-production-token'
            admin.execute("INSERT INTO sessions VALUES (%s,%s,'2099-01-01T00:00:00+00:00')", (hashlib.sha256(token.encode()).hexdigest(),uid))
        admin.execute("INSERT INTO products(id,farmer_id,name,price_grosze,delivery_grosze,stock) VALUES (1,3,'Product',100,100,10)")
        admin.execute("INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at) VALUES (1,1,3,1,1,100,100,200,'dostawa','w_drodze_testowo','CODE','private-pin-hash','2026-11-15')")
        admin.execute("INSERT INTO order_locations VALUES (1,NULL,'Private city','Private street','00-001')")
        admin.execute("INSERT INTO delivery_assignments VALUES (1,4,3,'2026-11-15')")
        admin.execute((ROOT/'database/security_review/001_roles.up.sql').read_text())
        with pytest.raises(psycopg.Error, match='compatibility not verified'):
            admin.execute((ROOT/'database/security_review/002_rls.up.sql').read_text())
        admin.execute('ROLLBACK')
        admin.execute("SET wp_security.compatibility_verified='yes'")
        admin.execute((ROOT/'database/security_review/002_rls.up.sql').read_text())
        # Physical connection as non-owner LOGIN, rather than a superuser SET ROLE.
        admin.execute('CREATE ROLE wp_security_test_login LOGIN IN ROLE wp_runtime')
    yield uri
    with psycopg.connect(uri, autocommit=True) as admin:
        admin.execute('DROP ROLE wp_security_test_login')
        admin.execute((ROOT/'database/security_review/002_rls.down.sql').read_text())
        admin.execute((ROOT/'database/security_review/001_roles.down.sql').read_text())
        assert admin.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='public.orders'::regclass").fetchone() == (False,False)
    server.cleanup()

@pytest.fixture
def runtime(cluster):
    with psycopg.connect(cluster, user='wp_security_test_login') as con:
        yield con


def identify(con, uid):
    con.execute("SELECT set_config('wiejskapaka.bearer', %s, true)", (f'opaque-test-session-{uid}-not-a-production-token',))


def test_role_and_no_context_are_fail_closed(runtime):
    assert runtime.execute('SELECT wp_security.actor_id()').fetchone() == (None,)
    assert runtime.execute('SELECT id FROM orders').fetchall() == []
    assert runtime.execute("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname=current_user").fetchone() == (False,)*5

@pytest.mark.parametrize('uid,expected', [(1,[1]),(2,[]),(3,[1]),(4,[1]),(5,[1])])
def test_order_isolation(runtime,uid,expected):
    identify(runtime,uid)
    assert [r[0] for r in runtime.execute('SELECT id FROM orders')] == expected

@pytest.mark.parametrize('uid,expected', [(1,1),(2,0),(3,0),(4,1),(5,0)])
def test_addresses_are_stricter_than_order_visibility(runtime,uid,expected):
    identify(runtime,uid)
    assert len(runtime.execute('SELECT delivery_street FROM order_locations').fetchall()) == expected

@pytest.mark.parametrize('uid', [1,2,3,4,5])
def test_spoofed_guc_and_stored_hash_are_not_credentials(runtime,uid):
    runtime.execute("SELECT set_config('wiejskapaka.actor_id', %s, true)",(str(uid),))
    runtime.execute("SELECT set_config('wiejskapaka.role', 'admin', true)")
    assert runtime.execute('SELECT id FROM orders').fetchall() == []
    digest=hashlib.sha256(b'opaque-test-session-1-not-a-production-token').hexdigest()
    runtime.execute("SELECT set_config('wiejskapaka.bearer', %s, true)",(digest,))
    assert runtime.execute('SELECT wp_security.actor_id()').fetchone() == (None,)

@pytest.mark.parametrize('sql', ['SELECT pin_hash FROM orders', 'SELECT token_hash FROM sessions',
    "UPDATE orders SET buyer_id=2", "UPDATE users SET role='admin'", 'DELETE FROM orders',
    "INSERT INTO sessions VALUES ('x',2,'2099-01-01')", 'SET ROLE wp_authenticator', 'SET ROLE wp_migrator',
    'ALTER TABLE orders DISABLE ROW LEVEL SECURITY'])
def test_sensitive_columns_writes_and_role_escalation_denied(runtime,sql):
    identify(runtime,1)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        runtime.execute(sql)


def test_context_cleanup_and_transaction_rollback(runtime):
    from backend.rls_session_context import session_context
    with session_context(runtime,'Bearer opaque-test-session-1-not-a-production-token') as uid:
        assert uid == 1
    assert runtime.execute('SELECT wp_security.actor_id()').fetchone() == (None,)
    identify(runtime,1)
    runtime.rollback()
    assert runtime.execute('SELECT wp_security.actor_id()').fetchone() == (None,)


def test_expired_and_revoked_session(cluster,runtime):
    with psycopg.connect(cluster,autocommit=True) as admin:
        admin.execute("INSERT INTO sessions VALUES (%s,1,'2000-01-01T00:00:00Z')",(hashlib.sha256(b'expired-token').hexdigest(),))
    runtime.execute("SELECT set_config('wiejskapaka.bearer','expired-token',true)")
    assert runtime.execute('SELECT wp_security.actor_id()').fetchone() == (None,)
    identify(runtime,5)
    assert runtime.execute('SELECT wp_security.actor_id()').fetchone() == (5,)
    with psycopg.connect(cluster,autocommit=True) as admin:
        admin.execute('DELETE FROM sessions WHERE user_id=5')
    assert runtime.execute('SELECT wp_security.actor_id()').fetchone() == (None,)


def test_every_private_table_has_all_four_policies(cluster):
    with psycopg.connect(cluster) as admin:
        rows=admin.execute("""SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,
            (SELECT count(*) FROM pg_policy p WHERE p.polrelid=c.oid AND p.polname IN ('wp_select','wp_insert','wp_update','wp_delete'))
            FROM wp_security.previous_rls s JOIN pg_class c ON c.oid=s.table_oid""").fetchall()
        assert len(rows)>30
        assert all(enabled and forced and count==4 for _,enabled,forced,count in rows)


def test_rls_denies_dml_even_if_table_grants_are_accidentally_broadened(cluster,runtime):
    # Exercise the policy boundary itself, not only missing GRANTs.
    with psycopg.connect(cluster,autocommit=True) as admin:
        admin.execute('GRANT INSERT,UPDATE,DELETE ON orders TO wp_runtime')
    try:
        identify(runtime,1)
        assert runtime.execute("UPDATE orders SET buyer_id=2,status='odebrane' WHERE id=1").rowcount==0
        assert runtime.execute('DELETE FROM orders WHERE id=1').rowcount==0
        with pytest.raises(psycopg.errors.InsufficientPrivilege,match='row-level security'):
            runtime.execute("INSERT INTO orders(id,buyer_id,farmer_id,product_id,quantity,subtotal_grosze,delivery_grosze,total_grosze,fulfillment,status,pickup_code,pin_hash,created_at) VALUES (2,2,3,1,1,100,100,200,'dostawa','w_drodze_testowo','FORGED','hash','2026-11-15')")
        runtime.rollback()
    finally:
        with psycopg.connect(cluster,autocommit=True) as admin:
            admin.execute('REVOKE INSERT,UPDATE,DELETE ON orders FROM wp_runtime')


def test_wallet_owner_cannot_mint_money_even_with_dml_grants(cluster,runtime):
    with psycopg.connect(cluster,autocommit=True) as admin:
        admin.execute('INSERT INTO wallet_preview_accounts(user_id,available_grosze) VALUES (1,100)')
        admin.execute('GRANT SELECT (user_id,available_grosze),UPDATE (available_grosze),INSERT (user_id,available_grosze) ON wallet_preview_accounts TO wp_runtime')
        admin.execute('GRANT DELETE ON wallet_preview_accounts TO wp_runtime')
    try:
        identify(runtime,1)
        assert runtime.execute('SELECT available_grosze FROM wallet_preview_accounts').fetchall()==[(100,)]
        assert runtime.execute('UPDATE wallet_preview_accounts SET available_grosze=100000 WHERE user_id=1').rowcount==0
        assert runtime.execute('DELETE FROM wallet_preview_accounts WHERE user_id=1').rowcount==0
        identify(runtime,2)
        assert runtime.execute('SELECT user_id FROM wallet_preview_accounts').fetchall()==[]
        with pytest.raises(psycopg.errors.InsufficientPrivilege,match='row-level security'):
            runtime.execute('INSERT INTO wallet_preview_accounts(user_id,available_grosze) VALUES (2,100000)')
        runtime.rollback()
    finally:
        with psycopg.connect(cluster,autocommit=True) as admin:
            admin.execute('REVOKE SELECT (user_id,available_grosze),UPDATE (available_grosze),INSERT (user_id,available_grosze) ON wallet_preview_accounts FROM wp_runtime')
            admin.execute('REVOKE DELETE ON wallet_preview_accounts FROM wp_runtime')


def test_runtime_preflight_checks_real_role_membership(cluster,runtime):
    from backend.postgres_runtime_role import assert_runtime_role
    assert_runtime_role(runtime)
    with psycopg.connect(cluster,autocommit=True) as admin:
        admin.execute('GRANT pg_read_all_data TO wp_runtime')
    try:
        with pytest.raises(RuntimeError,match='konto aplikacyjne'):
            assert_runtime_role(runtime)
    finally:
        with psycopg.connect(cluster,autocommit=True) as admin:
            admin.execute('REVOKE pg_read_all_data FROM wp_runtime')
    # The migration/owner connection must fail even with FORCE RLS enabled.
    with psycopg.connect(cluster) as admin:
        with pytest.raises(RuntimeError,match='konto aplikacyjne'):
            assert_runtime_role(admin)
