from tests.test_api import c, reg

def test_farmer_profile_points_and_address_permissions():
    farmer=reg('farmer3@example.com','rolnik')
    buyer=reg('buyer3@example.com','klient')
    stranger=reg('stranger3@example.com','klient')
    profile={'farm_name':'Zielone Pole','city':'Radom','description':'Warzywa lokalne'}
    assert c.put('/farmers/me/profile',json=profile,headers=farmer).status_code==200
    assert c.get('/farmers/me/profile',headers=farmer).json()==profile
    assert c.put('/farmers/me/profile',json=profile,headers=buyer).status_code==403
    p=c.post('/products',json={'name':'Marchew','price_grosze':199,'delivery_grosze':501,'stock':10},headers=farmer).json()['id']
    point=c.post('/pickup-points',json={'name':'Odbiór','city':'Radom','street':'Polna 3','opening_hours':'8:00-18:00'},headers=farmer).json()['id']
    assert c.post('/orders',json={'product_id':p,'quantity':1,'fulfillment':'odbior'},headers=buyer).status_code==422
    assert c.post('/orders',json={'product_id':p,'quantity':1,'fulfillment':'dostawa'},headers=buyer).status_code==422
    pickup=c.post('/orders',json={'product_id':p,'quantity':1,'fulfillment':'odbior','pickup_point_id':point},headers=buyer)
    assert pickup.status_code==201
    assert pickup.json()['total_grosze']==199
    delivery=c.post('/orders',json={'product_id':p,'quantity':2,'fulfillment':'dostawa','delivery_city':'Radom','delivery_street':'Leśna 5','delivery_postal_code':'26-600'},headers=buyer)
    assert delivery.status_code==201
    assert delivery.json()['total_grosze']==899
    oid=delivery.json()['id']
    assert c.get(f'/orders/{oid}/location',headers=stranger).status_code==403
    assert c.get(f'/orders/{oid}/location',headers=farmer).status_code==403
