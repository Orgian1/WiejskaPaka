from tests.test_api import c, reg

def test_cancel_restores_stock_and_restricts_owner():
    farmer=reg('stage2farmer@example.com','rolnik')
    buyer=reg('stage2buyer@example.com','klient')
    other=reg('stage2other@example.com','klient')
    pid=c.post('/products',json={'name':'Ziemniaki','price_grosze':101,'delivery_grosze':99,'stock':3},headers=farmer).json()['id']
    point=c.post('/pickup-points',json={'name':'Punkt','city':'Radom','street':'Polna 5','opening_hours':'8-16'},headers=farmer).json()['id']
    o=c.post('/orders',json={'product_id':pid,'quantity':3,'fulfillment':'odbior','pickup_point_id':point},headers=buyer).json()
    assert c.post(f'/orders/{o["id"]}/cancel-test',headers=other).status_code==404
    assert c.post(f'/orders/{o["id"]}/cancel-test',headers=buyer).status_code==200
    assert c.post(f'/orders/{o["id"]}/cancel-test',headers=buyer).status_code==409
    p=[x for x in c.get('/products').json() if x['id']==pid][0]
    assert p['stock']==3
    assert c.get('/auth/me',headers=farmer).json()['role']=='rolnik'
    assert any(x['id']==pid for x in c.get('/products/mine',headers=farmer).json())

def test_delivery_cannot_be_marked_as_pickup():
    farmer=reg('stage2farmer2@example.com','rolnik')
    buyer=reg('stage2buyer2@example.com','klient')
    pid=c.post('/products',json={'name':'Gruszki','price_grosze':333,'delivery_grosze':101,'stock':2},headers=farmer).json()['id']
    order=c.post('/orders',json={'product_id':pid,'quantity':1,'fulfillment':'dostawa','delivery_city':'Radom','delivery_street':'Polna 4','delivery_postal_code':'26-600'},headers=buyer).json()
    assert order['total_grosze']==434
    assert c.post(f'/test/orders/{order["id"]}/ready',headers=farmer).status_code==409

def test_ui_served():
    assert c.get('/').status_code==200
    assert 'WiejskaPaka' in c.get('/').text
    assert c.get('/assets/app.js').status_code==200
