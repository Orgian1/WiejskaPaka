"""Signed SQL still obeys rating eligibility, privacy and immutable storage."""
from pathlib import Path
import pytest
from tests.test_rls_gateway_postgres import secured,raw,psycopg
from backend.pg_adapter import PgConnection
from backend.rls_gateway import database_context

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def rated(secured):
    with psycopg.connect(secured[0],autocommit=True) as admin:
        admin.execute("UPDATE orders SET status='odebrane',pin_used=1,confirmed_at='2026-11-16T00:00:00Z' WHERE id=1")
        admin.execute('INSERT INTO seller_ratings(order_id,buyer_id,farmer_id,stars) VALUES(1,1,3,5)')
    return secured


@pytest.mark.parametrize('actor,expected',[(1,[1]),(2,[]),(3,[]),(5,[]),(7,[1])])
def test_rating_row_privacy_and_public_aggregate(raw,rated,actor,expected):
    raw.execute("SELECT set_config('wiejskapaka.actor_id','7',true),set_config('wiejskapaka.role','admin',true)")
    with database_context('request','Bearer '+rated[2][actor]):
        con=PgConnection(raw)
        assert [r['order_id'] for r in con.execute('SELECT order_id FROM seller_ratings').fetchall()]==expected
        assert con.execute('SELECT * FROM wp_rls.seller_rating_summary(3)').fetchone()=={'count':1,'total':5}


@pytest.mark.parametrize('statement,actor',[
 ('INSERT INTO seller_ratings(order_id,buyer_id,farmer_id,stars) VALUES(2,2,4,5)',1),
 ('INSERT INTO seller_ratings(order_id,buyer_id,farmer_id,stars) VALUES(2,2,4,5)',2),
 ('INSERT INTO seller_ratings(order_id,buyer_id,farmer_id,stars) VALUES(1,1,4,5)',1),
 ('UPDATE seller_ratings SET stars=1 WHERE order_id=1',1),
 ('DELETE FROM seller_ratings WHERE order_id=1',1),
 ('UPDATE seller_ratings SET stars=1 WHERE order_id=1',7),
])
def test_forbidden_rating_writes(raw,rated,statement,actor):
    with database_context('request','Bearer '+rated[2][actor]):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):PgConnection(raw).execute(statement)


def test_rating_raw_login_cannot_read_rows(raw,rated):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):raw.execute('SELECT * FROM seller_ratings')


def test_ratings_upgrade_rollback_preserves_orders_and_wallet(rated):
    with psycopg.connect(rated[0],autocommit=True) as con:
        before=con.execute('SELECT id,status,pin_used,total_grosze FROM orders ORDER BY id').fetchall()
        wallet=con.execute('SELECT * FROM wallet_preview_accounts ORDER BY user_id').fetchall()
        con.execute((ROOT/'database/security_rls/003_seller_ratings.down.sql').read_text())
        assert con.execute("SELECT to_regclass('seller_ratings')").fetchone()==(None,)
        with pytest.raises(psycopg.Error,match='compatibility verification'):con.execute((ROOT/'database/security_rls/003_seller_ratings.up.sql').read_text())
        con.execute('ROLLBACK');con.execute("SET wp_rls.disposable_test='yes'")
        con.execute((ROOT/'database/security_rls/003_seller_ratings.up.sql').read_text())
        assert con.execute('SELECT id,status,pin_used,total_grosze FROM orders ORDER BY id').fetchall()==before
        assert con.execute('SELECT * FROM wallet_preview_accounts ORDER BY user_id').fetchall()==wallet
        assert con.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='seller_ratings'::regclass").fetchone()==(True,True)


def test_unknown_rating_policy_blocks_migration_and_rollback(rated):
    with psycopg.connect(rated[0],autocommit=True) as con:
        con.execute('CREATE POLICY custom_rating_policy ON seller_ratings USING(false)')
        try:
            for name in ('003_seller_ratings.up.sql','003_seller_ratings.down.sql'):
                con.execute("SET wp_rls.disposable_test='yes'")
                with pytest.raises(psycopg.Error,match='Unknown ratings policy'):con.execute((ROOT/'database/security_rls'/name).read_text())
                con.execute('ROLLBACK')
        finally:con.execute('DROP POLICY custom_rating_policy ON seller_ratings')
