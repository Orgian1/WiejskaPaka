"""Real HTTP: unverified checkout must leave no order, PIN, hold or mail job."""
from contextlib import closing
import sqlite3
import pytest
from tests.test_email_verification_http import enabled,queued
from tests.test_order_mail_capture_http import setup,order
from tests.test_purchase_record_http_restart import server


def snapshot(database,pid):
    with closing(sqlite3.connect(database)) as con:
        return {**{table:con.execute('SELECT count(*) FROM '+table).fetchone()[0]
                   for table in ('orders','checkout_idempotency','inventory_reservations','order_mail_outbox')},
                'stock':con.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()[0]}


@pytest.mark.parametrize('cart',[False,True])
def test_unverified_account_blocked_then_confirmed_account_can_buy(enabled,monkeypatch,cart):
    database,keys,key_path=enabled
    monkeypatch.setenv('WP_REQUIRE_VERIFIED_EMAIL_FOR_CHECKOUT','1')
    with server(database,verification_keys=key_path,order_mail=True) as client:
        buyer,pid=setup(client,False,database,keys)
        if cart:assert client.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':1}).status_code==200
        before=snapshot(database,pid)
        blocked=order(client,buyer,pid,cart)
        assert blocked.status_code==403 and 'Potwierdź adres e-mail' in blocked.json()['detail']
        assert 'pin_test_only' not in blocked.text and snapshot(database,pid)==before
        assert client.post('/auth/email-verification/request',headers=buyer).status_code==202
        secret=queued(database,keys).token
        assert order(client,buyer,pid,cart).status_code==403  # Issuing a link is not proof.
        assert client.post('/auth/email-verification/confirm',headers=buyer,json={'token':secret}).status_code==200
        completed=order(client,buyer,pid,cart)
        assert completed.status_code==201,completed.text
        assert snapshot(database,pid)['stock']==4
        assert snapshot(database,pid)['order_mail_outbox']==1
        assert order(client,buyer,pid,cart).json()==completed.json()
        with closing(sqlite3.connect(database)) as con:
            con.execute('UPDATE account_email_proofs SET verified_at=NULL');con.commit()
        after=snapshot(database,pid)
        assert order(client,buyer,pid,cart).status_code==403  # Cached reply cannot expose its PIN.
        assert snapshot(database,pid)==after


@pytest.mark.parametrize('cart',[False,True])
def test_proof_for_another_email_cannot_authorize_checkout(enabled,monkeypatch,cart):
    database,keys,key_path=enabled
    monkeypatch.setenv('WP_REQUIRE_VERIFIED_EMAIL_FOR_CHECKOUT','1')
    with server(database,verification_keys=key_path,order_mail=True) as client:
        buyer,pid=setup(client,True,database,keys)
        if cart:assert client.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':1}).status_code==200
        with closing(sqlite3.connect(database)) as con:
            con.execute('UPDATE account_email_proofs SET email_hash=?',('0'*64,));con.commit()
        before=snapshot(database,pid)
        assert order(client,buyer,pid,cart).status_code==403
        assert snapshot(database,pid)==before


def test_preflight_rejects_checkout_requirement_without_verification():
    from backend.test_server_launcher import prepare_test_server,required_preview_tables
    env={'WP_REQUIRE_VERIFIED_EMAIL_FOR_CHECKOUT':'1'}
    assert 'account_email_proofs' in required_preview_tables({**env,'WP_ENABLE_EMAIL_VERIFICATION':'1'})
    with pytest.raises(ValueError,match='Checkout requires enabled email verification'):
        prepare_test_server(env)
