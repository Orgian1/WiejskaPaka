from tests.test_api import c, reg

def test_delivery_assignment_and_audit():
    farmer=reg('farmer9@example.com','rolnik')
    buyer=reg('buyer9@example.com','klient')
    courier=reg('courier9@example.com','dostawca')
    stranger=reg('stranger9@example.com','dostawca')
    pid=c.post('/products',json={'name':'Ziemniaki','price_grosze':1299,'delivery_grosze':499,'stock':3},headers=farmer).json()['id']
    order=c.post('/orders',json={'product_id':pid,'quantity':1,'fulfillment':'dostawa','delivery_city':'Radom','delivery_street':'Polna 12','delivery_postal_code':'26-600'},headers=buyer)
    assert order.status_code==201
    oid=order.json()['id']
    cid=c.get('/auth/me',headers=courier).json()['id']
    assert c.post(f'/orders/{oid}/assign-courier-test',json={'courier_id':cid},headers=buyer).status_code==403
    assert c.post(f'/orders/{oid}/assign-courier-test',json={'courier_id':cid},headers=farmer).status_code==200
    assert c.post(f'/orders/{oid}/assign-courier-test',json={'courier_id':cid},headers=farmer).status_code==409
    assert c.post(f'/orders/{oid}/dispatch-test',headers=farmer).status_code==200
    assert c.get('/couriers/me/orders',headers=courier).json()[0]['id']==oid
    assert c.get(f'/orders/{oid}/events',headers=stranger).status_code==403
    assert len(c.get(f'/orders/{oid}/events',headers=buyer).json())==3
    assert c.post(f'/orders/{oid}/confirm',json={'pin':order.json()['pin_test_only'],'checked_goods':True},headers=stranger).status_code==403
    assert c.post(f'/orders/{oid}/confirm',json={'pin':order.json()['pin_test_only'],'checked_goods':True},headers=courier).json()['confirmed'] is True
    assert c.get(f'/orders/{oid}/events',headers=buyer).json()[-1]['new_status']=='odebrane'
