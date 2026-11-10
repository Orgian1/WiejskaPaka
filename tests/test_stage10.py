from tests.test_api import c, reg

def test_notification_inbox_is_private_and_read_is_idempotent():
    farmer=reg('farmer10@example.com','rolnik')
    buyer=reg('buyer10@example.com','klient')
    stranger=reg('stranger10@example.com','klient')
    product=c.post('/products',json={'name':'Jabłka','price_grosze':999,'delivery_grosze':499,'stock':2},headers=farmer).json()['id']
    order=c.post('/orders',json={'product_id':product,'quantity':1,'fulfillment':'dostawa','delivery_city':'Łódź','delivery_street':'Polna 4','delivery_postal_code':'90-001'},headers=buyer)
    assert order.status_code==201,order.text
    inbox=c.get('/notifications/me',headers=buyer).json()
    assert inbox and inbox[0]['event_type']=='order_created'
    assert c.get('/notifications/me/unread-count',headers=buyer).json()['unread']>=1
    note_id=inbox[0]['id']
    assert c.post(f'/notifications/{note_id}/read',headers=stranger).status_code==404
    assert c.post(f'/notifications/{note_id}/read',headers=buyer).status_code==200
    assert c.post(f'/notifications/{note_id}/read',headers=buyer).status_code==200
    assert c.get('/notifications/me',headers=stranger).json()==[]
    assert c.get('/notifications/me',headers=farmer).json()[0]['order_id']==order.json()['id']
    assert c.get('/notifications/me?limit=101',headers=buyer).status_code==422
