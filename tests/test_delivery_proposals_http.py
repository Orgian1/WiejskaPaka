"""Schedule negotiation, ownership, revisions and shipment-wide transactions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta,timezone
import json
import pytest
from backend import app as module
from tests.test_address_delivery_http import actors as shared_actors,create,setup,new_product,decide,stock


@pytest.fixture
def actors():
    # Fresh accounts per scenario preserve the real ten-unpaid-purchase limit.
    yield from shared_actors.__wrapped__()


def terms(body,revision=0,days=1):
    return {'revision':revision,'delivery_date':(date.fromisoformat(body['address_delivery']['delivery_date'])+timedelta(days=days)).isoformat(),'from_time':'09:30','to_time':'11:30'}


def propose(client,farmer,oid,payload):return client.post(f'/address-delivery/requests/{oid}/proposal',headers=farmer,json=payload)
def answer(client,buyer,proposal,decision='accepted'):
    return client.post('/address-delivery/proposals/'+proposal['id']+'/decision',headers=buyer,json={'decision':decision,'revision':proposal['request_revision']})
def request(client,owner,oid):return next(r for r in client.get('/address-delivery/requests/mine',headers=owner).json()['items'] if r['order_id']==oid)


def test_buyer_must_accept_new_date_and_hours_before_payment(actors):
    client,users,pid,body,oid=create(actors);seller,buyer=users[0][0],users[2][0]
    payload=terms(body);result=propose(client,seller,oid,payload)
    assert result.status_code==200;proposal=result.json()['proposal'];assert proposal['state']=='pending'
    event={'event_id':'reschedule-paid','event_type':'payment_success_test'}
    assert client.post(f'/test/payments/{oid}/events',headers=buyer,json=event).status_code==409
    assert decide(client,seller,oid,'accepted',1).status_code==409
    assert request(client,buyer,oid)['delivery_date']==body['address_delivery']['delivery_date']
    assert answer(client,buyer,proposal).status_code==200
    agreed=request(client,buyer,oid)
    assert agreed['state']=='accepted' and agreed['delivery_date']==payload['delivery_date']
    assert (agreed['agreed_from'],agreed['agreed_to'],agreed['customer_from'],agreed['customer_to'])==(570,690,570,690)
    assert 'phone' not in json.dumps(agreed) and '500100200' not in json.dumps(agreed)
    assert stock(pid)==8
    assert client.post(f'/test/payments/{oid}/events',headers=buyer,json=event).status_code==200
    assert answer(client,buyer,proposal).json()['already_processed']


def test_proposals_and_decisions_are_scoped_to_both_parties(actors):
    client,users,pid,body,oid=create(actors);payload=terms(body)
    assert propose(client,users[2][0],oid,payload).status_code==403
    assert propose(client,users[1][0],oid,payload).status_code==404
    result=propose(client,users[0][0],oid,payload).json()['proposal']
    assert answer(client,users[3][0],result).status_code==404
    assert answer(client,users[0][0],result).status_code==403
    assert answer(client,users[4][0],result).status_code==403
    assert answer(client,{},result).status_code==401
    assert request(client,users[2][0],oid)['state']=='pending' and stock(pid)==8


def test_superseded_and_stale_decisions_cannot_change_a_newer_schedule(actors):
    client,users,_,body,oid=create(actors);seller,buyer=users[0][0],users[2][0]
    first=propose(client,seller,oid,terms(body)).json()['proposal']
    latest=propose(client,seller,oid,terms(body,revision=1,days=2)).json()['proposal']
    assert answer(client,buyer,first).status_code==409
    assert answer(client,buyer,latest).status_code==200
    assert answer(client,buyer,latest,'declined').status_code==409
    replay=propose(client,seller,oid,terms(body))
    assert replay.status_code==200 and replay.json()['already_processed']
    assert request(client,buyer,oid)['proposal']['id']==latest['id']


def test_rejected_proposal_keeps_original_pending_order_and_stock_hold(actors):
    client,users,pid,body,oid=create(actors);seller,buyer=users[0][0],users[2][0]
    proposal=propose(client,seller,oid,terms(body)).json()['proposal']
    assert answer(client,buyer,proposal,'declined').status_code==200
    row=request(client,buyer,oid)
    assert row['state']=='pending' and row['revision']==2 and row['delivery_date']==body['address_delivery']['delivery_date']
    assert stock(pid)==8
    assert decide(client,seller,oid,'accepted',revision=2).status_code==200


def test_concurrent_proposal_retries_and_conflicting_buyer_decisions(actors):
    client,users,pid,body,oid=create(actors);seller,buyer=users[0][0],users[2][0];payload=terms(body)
    with ThreadPoolExecutor(max_workers=4) as pool:replies=list(pool.map(lambda _:propose(client,seller,oid,payload),range(4)))
    assert all(r.status_code==200 for r in replies) and sum(not r.json()['already_processed'] for r in replies)==1
    proposal=replies[0].json()['proposal'];assert len({r.json()['proposal']['id'] for r in replies})==1
    with ThreadPoolExecutor(max_workers=2) as pool:decisions=list(pool.map(lambda decision:answer(client,buyer,proposal,decision),['accepted','declined']))
    assert sorted(r.status_code for r in decisions)==[200,409]
    assert stock(pid)==8
    with module.db() as con:
        assert con.execute('SELECT count(*) AS n FROM delivery_schedule_proposals WHERE anchor_order_id=?',(oid,)).fetchone()['n']==1


@pytest.mark.parametrize('change',[{'from_time':'12:00','to_time':'11:00'},{'delivery_date':'2000-01-01'},{'delivery_date':'2026-02-30'},{'from_time':'25:00'},{'phone':'must-not-be-accepted'}])
def test_invalid_terms_do_not_mutate_request(actors,change):
    client,users,pid,body,oid=create(actors)
    assert propose(client,users[0][0],oid,{**terms(body),**change}).status_code==422
    assert request(client,users[2][0],oid)['revision']==0 and stock(pid)==8


def test_expired_reservation_cannot_be_extended_by_a_proposal(actors):
    client,users,pid,body,oid=create(actors)
    with module.db() as con:con.execute('UPDATE inventory_reservations SET expires_at=? WHERE order_id=?',((datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),oid))
    assert propose(client,users[0][0],oid,terms(body)).status_code==409


def test_entire_shipment_agrees_atomically_and_preserves_one_shipping_fee(actors):
    client,users,pid,body=setup(actors);seller,buyer=users[0][0],users[2][0]
    other=new_product(client,seller)
    for product in (pid,other):assert client.put('/cart/items',headers=buyer,json={'product_id':product,'quantity':1}).status_code==200
    payload={k:v for k,v in body.items() if k not in ('product_id','quantity')}
    receipt=client.post('/cart/checkout-test',headers=buyer,json=payload)
    assert receipt.status_code==201,receipt.text
    receipt=receipt.json();assert receipt['delivery_grosze']==500
    ids=[o['id'] for o in receipt['orders']]
    proposal=propose(client,seller,ids[-1],terms(body)).json()['proposal']
    assert decide(client,seller,ids[0],'accepted',revision=1).status_code==409
    assert answer(client,buyer,proposal).status_code==200
    for oid in ids:
        row=request(client,buyer,oid);assert row['proposal']['id']==proposal['id'] and row['state']=='accepted'
        assert row['agreed_from']==570 and row['delivery_date']==terms(body)['delivery_date']
    with module.db() as con:
        totals=con.execute('SELECT SUM(delivery_grosze) AS shipping,SUM(total_grosze) AS total FROM orders WHERE id IN (?,?)',tuple(ids)).fetchone()
        assert totals['shipping']==500 and totals['total']==receipt['total_grosze']
