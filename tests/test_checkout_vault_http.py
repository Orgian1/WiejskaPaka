"""Actual process restarts, key rotation/loss and post-retention HTTP replay."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
import json
import sqlite3
import os
import pytest
from tests.test_purchase_record_http_restart import server,setup
from backend.checkout_vault import read_ring,rotate_ring,Vault,CheckoutStorageError


def create(client,buyer,pid,cart=False):
    key='vault-http-'+('cart' if cart else 'direct')
    body={'fulfillment':'dostawa','delivery_city':'Opole','delivery_street':'Prywatna 9','delivery_postal_code':'45-001'}
    if cart:
        assert client.put('/cart/items',headers=buyer,json={'product_id':pid,'quantity':1}).status_code==200
        url='/cart/checkout-test'
    else:body.update(product_id=pid,quantity=1);url='/orders'
    headers={**buyer,'Idempotency-Key':key}
    r=client.post(url,headers=headers,json=body);assert r.status_code==201,r.text
    return key,body,url,headers,r.json()


@pytest.mark.parametrize('cart',[False,True])
def test_real_http_replay_after_restart_rotation_and_expiry(tmp_path,cart):
    database=tmp_path/'http.sqlite3';keyfile=tmp_path/'http.sqlite3.checkout-key'
    with server(database) as client:
        farmer,buyer,products=setup(client)
        key,body,url,headers,result=create(client,buyer,products[0],cart)
    with closing(sqlite3.connect(database)) as con, con:
        con.row_factory=sqlite3.Row;row=con.execute('SELECT * FROM checkout_idempotency').fetchone()
        assert all(s not in row['response_json'] for s in ('pin_test_only','Prywatna 9'))
        count=con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    previous_id=read_ring(keyfile)[0]
    if os.name == 'posix':
        rotate_ring(keyfile)
        assert read_ring(keyfile)[0]!=previous_id
    else:
        before_key=keyfile.read_bytes()
        with pytest.raises(CheckoutStorageError, match='POSIX'):rotate_ring(keyfile)
        assert keyfile.read_bytes()==before_key
    # Restart, replay and retention are exercised on every supported platform.
    with server(database) as client:
        response=client.post(url,headers=headers,json=body)
        assert response.status_code==201 and response.json()==result
        assert response.headers['cache-control']=='no-store'
        if not cart:
            status=client.get('/orders/idempotency-status/'+key,headers=buyer)
            assert status.json()=={'completed':True,'order_id':result['id']}
            assert 'pin' not in status.text.lower()
    active,keys=read_ring(keyfile);v=Vault(active,keys)
    # Simulate an authenticated old reply; do not bypass authentication by editing TTL.
    with closing(sqlite3.connect(database)) as con, con:
        sealed=v.seal(result,row['buyer_id'],row['request_key'],row['payload_hash'],
                      pin_until=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        con.execute('UPDATE checkout_idempotency SET response_json=?',(sealed,))
    with server(database) as client:
        response=client.post(url,headers=headers,json=body)
        assert response.status_code==201 and response.json()['pin_available'] is False
        assert 'pin_test_only' not in response.text
    with closing(sqlite3.connect(database)) as con, con:
        current=con.execute('SELECT response_json FROM checkout_idempotency').fetchone()[0]
        assert json.loads(current)['pin_state']=='redacted'
        assert 'pin_test_only' not in v._decrypt(current,row['buyer_id'],row['request_key'],row['payload_hash'])[0]
        assert con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==count
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


@pytest.mark.parametrize('problem',['missing','wrong'])
def test_real_startup_does_not_replace_missing_or_wrong_key(tmp_path,problem):
    database=tmp_path/'fail.sqlite3';keyfile=tmp_path/'fail.sqlite3.checkout-key'
    with server(database) as client:
        farmer,buyer,products=setup(client);create(client,buyer,products[0])
    before=database.read_bytes();original=keyfile.read_bytes()
    if problem=='missing':keyfile.unlink()
    else:
        from backend.checkout_vault import create_ring
        wrong=tmp_path/'wrong.checkout-key';create_ring(wrong);keyfile.write_bytes(wrong.read_bytes())
    with pytest.raises(AssertionError):
        with server(database):pytest.fail('Unsafe server started')
    assert database.read_bytes()==before
    if problem=='missing':assert not keyfile.exists()
    else:assert keyfile.read_bytes()!=original
