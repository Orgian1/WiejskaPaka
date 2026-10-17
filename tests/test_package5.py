from pathlib import Path
from backend.release_audit import release_report
from tests.test_api import c, reg

ROOT = Path(__file__).resolve().parents[1]

def test_release_report_not_claim_production_ready():
    result=release_report(ROOT, {'WP_ENABLE_TEST_PAYMENTS':'0','WP_ENABLE_WEEKLY_JOB':'0'})
    assert result['ready_for_production'] is False
    assert result['automated_errors']==0
    assert any(x['severity']=='manual' and not x['passed'] for x in result['checks'])

def test_release_report_flags_unsafe_configuration():
    result=release_report(ROOT, {'WP_ENABLE_TEST_PAYMENTS':'1','WP_ENABLE_WEEKLY_JOB':'1'})
    assert sum(not x['passed'] for x in result['checks'] if x['severity']=='warning')==2

def test_mobile_accessibility_structure():
    html=(ROOT/'web/index.html').read_text()
    css=(ROOT/'web/style.css').read_text()
    assert 'href="#tresc"' in html and 'id="tresc"' in html
    assert 'prefers-reduced-motion' in css and 'focus-visible' in css

def test_purchase_delivery_end_to_end_smoke():
    farmer=reg('finalfarmer@example.org','rolnik')
    buyer=reg('finalbuyer@example.org','klient')
    courier=reg('finalcourier@example.org','dostawca')
    product=c.post('/products',json={'name':'Gruszki','price_grosze':1533,'delivery_grosze':467,'stock':1},headers=farmer)
    assert product.status_code==201
    order=c.post('/orders',json={'product_id':product.json()['id'],'quantity':1,'fulfillment':'dostawa','delivery_city':'Łódź','delivery_street':'Polna 7','delivery_postal_code':'90-001'},headers=buyer)
    assert order.status_code==201
    data=order.json(); assert data['total_grosze']==2000
    assert c.post('/orders',json={'product_id':product.json()['id'],'quantity':1,'fulfillment':'dostawa','delivery_city':'Łódź','delivery_street':'Polna 7','delivery_postal_code':'90-001'},headers=buyer).status_code==409
    courier_id=c.get('/auth/me',headers=courier).json()['id']
    assert c.post(f"/orders/{data['id']}/assign-courier-test",json={'courier_id':courier_id},headers=farmer).status_code==200
    assert c.post(f"/orders/{data['id']}/dispatch-test",headers=farmer).status_code==200
    assert c.post(f"/orders/{data['id']}/confirm",json={'pin':data['pin_test_only'],'checked_goods':False},headers=courier).status_code in (400,409,422)
    assert c.post(f"/orders/{data['id']}/confirm",json={'pin':data['pin_test_only'],'checked_goods':True},headers=courier).json()['confirmed'] is True
    assert c.get(f"/orders/{data['id']}/events",headers=buyer).status_code==200
