"""Product reminder counts completed purchases, not product rows or legal thresholds."""
import sqlite3
import pytest
from backend.seller_compliance import seller_compliance_status, acknowledge_seller_rules, review_seller_account, create_compliance_tables, RULES_VERSION
from tests.test_purchase_record_http_restart import server, account

@pytest.fixture
def con():
    with sqlite3.connect(':memory:') as db:
        db.row_factory=sqlite3.Row
        db.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY,role TEXT);
            INSERT INTO users VALUES(1,'rolnik'),(2,'admin'),(3,'klient'),(4,'rolnik');
            CREATE TABLE orders(id INTEGER PRIMARY KEY,farmer_id INTEGER,buyer_id INTEGER,status TEXT);
            CREATE TABLE shipment_groups(id TEXT PRIMARY KEY,farmer_id INTEGER,buyer_id INTEGER);
            CREATE TABLE shipment_order_links(order_id INTEGER PRIMARY KEY,shipment_id TEXT);''')
        create_compliance_tables(db)
        yield db


def shipment(con, name, statuses, farmer=1, buyer=3):
    con.execute('INSERT INTO shipment_groups VALUES(?,?,?)', (name,farmer,buyer))
    for status in statuses:
        row=con.execute('INSERT INTO orders(farmer_id,buyer_id,status) VALUES(?,?,?)',(farmer,buyer,status))
        con.execute('INSERT INTO shipment_order_links VALUES(?,?)',(row.lastrowid,name))


@pytest.mark.parametrize('completed', [0,19,20,21])
def test_threshold_counts_whole_shipments_and_unlinked_legacy_orders(con, completed):
    for index in range(completed):
        if index % 2:
            shipment(con,str(index),['odebrane']*3)
        else:
            con.execute("INSERT INTO orders(farmer_id,buyer_id,status) VALUES(1,3,'odebrane')")
    shipment(con,'partial',['odebrane','gotowe_do_odbioru_testowo'])
    shipment(con,'cancelled',['anulowane_testowo']*2)
    shipment(con,'failed',['nieudana_dostawa_testowo']*2)
    shipment(con,'pending',['oczekuje_na_platnosc_testowa']*2)
    shipment(con,'other-seller',['odebrane']*2,farmer=4)
    shipment(con,'empty',[])
    result=seller_compliance_status(con,1)
    assert result['completed_transaction_count']==completed
    assert result['profile_reminder_due']==(completed>=20)
    assert result['threshold_basis']=='product_rule_not_legal_threshold'
    assert not result['can_receive_real_payouts']
    assert result['identity_data_collection']=='disabled_until_secure_provider'


def test_acknowledgement_does_not_clear_reminder_or_enable_real_payouts(con):
    for index in range(20):shipment(con,str(index),['odebrane','odebrane'])
    acknowledge_seller_rules(con,1,RULES_VERSION)
    assert seller_compliance_status(con,1)['profile_reminder_due']
    review_seller_account(con,1,2,'approved','Tylko przegląd testowy')
    result=seller_compliance_status(con,1)
    assert not result['profile_reminder_due'] and not result['can_receive_real_payouts']
    review_seller_account(con,1,2,'needs_information','Wyjaśnienie testowe')
    assert seller_compliance_status(con,1)['profile_reminder_due']


def test_mixed_ownership_does_not_count_as_completed(con):
    shipment(con,'mixed',['odebrane','odebrane'])
    con.execute('UPDATE orders SET farmer_id=4 WHERE id=1')
    assert seller_compliance_status(con,1)['completed_transaction_count']==0
    con.execute('UPDATE orders SET farmer_id=1,buyer_id=2 WHERE id=1')
    assert seller_compliance_status(con,1)['completed_transaction_count']==0


def test_http_role_isolation_explicit_consent_and_idempotence(tmp_path):
    with server(tmp_path/'seller.sqlite3') as client:
        farmer, other, buyer=account(client,'rolnik'),account(client,'rolnik'),account(client,'klient')
        url='/farmers/me/compliance'
        assert client.get(url).status_code==401
        assert client.get(url,headers=buyer).status_code==403
        assert client.post(url+'/acknowledge',headers=farmer,json={'rules_version':RULES_VERSION,'accepted':False}).status_code==422
        for _ in range(2):
            response=client.post(url+'/acknowledge',headers=farmer,json={'rules_version':RULES_VERSION,'accepted':True})
            assert response.status_code==200
            assert response.json()['review_status']=='pending'
            assert response.json()['current_rules_version']==RULES_VERSION
        assert client.get(url,headers=other).json()['review_status']=='not_started'
        assert client.get(url,headers=farmer).json()['completed_transaction_count']==0
        assert client.post('/admin/farmers/1/compliance/review',headers=farmer,json={'decision':'approved','reason':'Próba'}).status_code==403
    with sqlite3.connect(tmp_path/'seller.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM seller_compliance_events').fetchone()[0]==1


def exercise_completed_shipment(client):
    """Shared real HTTP contract for SQLite and the restricted PostgreSQL role."""
    from uuid import uuid4
    farmer,buyer=account(client,'rolnik'),account(client,'klient')
    response=client.post('/pickup-points',headers=farmer,json={'name':'Punkt testowy','city':'Testowo','street':'Polna 1','opening_hours':'9:00–17:00'})
    assert response.status_code==201,response.text
    point=response.json()['id']
    for name in ('Marchew testowa','Ziemniaki testowe'):
        response=client.post('/products',headers=farmer,json={'name':name,'price_grosze':199,'delivery_grosze':501,'stock':10})
        assert response.status_code==201,response.text
        assert client.put('/cart/items',headers=buyer,json={'product_id':response.json()['id'],'quantity':1}).status_code==200
    response=client.post('/cart/checkout-test',headers={**buyer,'Idempotency-Key':uuid4().hex},json={'fulfillment':'odbior','pickup_point_id':point})
    assert response.status_code==201,response.text
    receipt=response.json()
    url='/farmers/me/compliance'
    for index,order in enumerate(receipt['orders']):
        response=client.post(f'/test/orders/{order["id"]}/ready',headers=farmer)
        assert response.status_code==200,response.text
        assert client.get(url,headers=farmer).json()['completed_transaction_count']==0
    response=client.post(f'/shipments/{receipt["shipment_id"]}/confirm',headers=farmer,json={'pin':receipt['shipment_pin_test_only'],'checked_goods':True})
    assert response.status_code==200 and response.json()['confirmed'],response.text
    result=client.get(url,headers=farmer)
    assert result.status_code==200,result.text
    assert result.json()['completed_transaction_count']==1
    assert result.json()['order_count_observed']==2
    assert not result.json()['profile_reminder_due']
    consent=client.post(url+'/acknowledge',headers=farmer,json={'rules_version':RULES_VERSION,'accepted':True})
    assert consent.status_code==200,consent.text
    assert consent.json()['rules_acknowledged'] and not consent.json()['can_receive_real_payouts']


def test_received_multi_item_shipment_http_contract(tmp_path):
    with server(tmp_path/'complete.sqlite3') as client:
        exercise_completed_shipment(client)
