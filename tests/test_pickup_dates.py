from datetime import date, timedelta
import pytest
from backend import pickup_dates
from tests.test_purchase_record_http_restart import server, account


def test_calendar_date_validation():
    now=date(2026,10,25)
    assert pickup_dates.validate(['2026-11-01','2026-10-25'],current=now)==['2026-10-25','2026-11-01']
    for values in ([],['2026-10-24'],['2028-01-01'],['2026-10-25']*2,['20261025'],[False],['2026-02-30']):
        with pytest.raises(ValueError):pickup_dates.validate(values,current=now)


def test_attendance_persists_and_other_seller_cannot_change_it(tmp_path,monkeypatch):
    monkeypatch.setenv('WP_ENABLE_PICKUP_DATES','1')
    day=(pickup_dates.today()+timedelta(days=3)).isoformat()
    body={'name':'Punkt targowy','city':'Legnica','street':'Polna 10','opening_hours':'10:00–12:00','attendance_dates':[day]}
    database=tmp_path/'calendar.sqlite'
    with server(database) as client:
        seller=account(client,'rolnik');other=account(client,'rolnik');buyer=account(client,'klient')
        assert client.get('/pickup-point-dates/config').json()['enabled'] is True
        assert client.post('/pickup-points',headers=buyer,json=body).status_code==403
        response=client.post('/pickup-points',headers=seller,json=body)
        assert response.status_code==201,response.text
        point=response.json()['id']
        assert client.get('/farmers/me/pickup-points',headers=seller).json()[0]['attendance_dates']==[day]
        assert client.put(f'/pickup-points/{point}',headers=other,json={**body,'active':True}).status_code==404
        seller_id=client.get('/auth/me',headers=seller).json()['id']
        assert client.get(f'/farmers/{seller_id}/pickup-points').json()[0]['attendance_dates']==[day]
        invalid={**body,'attendance_dates':['2020-01-01']}
        assert client.put(f'/pickup-points/{point}',headers=seller,json={**invalid,'active':True}).status_code==422
        # Sellers cannot purchase, even by calling API directly.
        product=client.post('/products',headers=other,json={'name':'Pomidory','price_grosze':200,'delivery_grosze':0,'stock':10}).json()
        own=client.post('/products',headers=seller,json={'name':'Ogórki','price_grosze':200,'delivery_grosze':0,'stock':10}).json()
        order=client.post('/orders',headers=buyer,json={'product_id':own['id'],'quantity':1,'fulfillment':'odbior','pickup_point_id':point})
        assert order.status_code==201,order.text
        changed={**body,'active':True,'attendance_dates':[(pickup_dates.today()+timedelta(days=4)).isoformat()]}
        assert client.put(f'/pickup-points/{point}',headers=seller,json=changed).status_code==409
        assert client.put('/cart/items',headers=seller,json={'product_id':product['id'],'quantity':1}).status_code==403
        assert client.post('/orders',headers=seller,json={'product_id':product['id'],'quantity':1,'fulfillment':'odbior','pickup_point_id':point}).status_code==403
    with server(database) as client:
        import sqlite3
        con=sqlite3.connect(database)
        assert con.execute('SELECT attendance_date FROM pickup_point_dates WHERE point_id=?',(point,)).fetchall()==[(day,)]
        con.close()
