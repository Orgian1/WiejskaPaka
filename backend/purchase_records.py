"""Insert-only records of test purchase terms, not invoices or proof of payment.

Never backfill original names/locations from today's catalog. No customer
address, PIN, credential, phone, tax ID or bank details are stored here.
"""
from datetime import datetime,timezone

COLUMNS=('order_id','buyer_id','farmer_id','product_id','pickup_code','product_name','unit_price_grosze','quantity',
         'subtotal_grosze','delivery_grosze','total_grosze','fulfillment','pickup_point_id',
         'point_name','point_city','point_street','point_opening_hours','latitude_e6','longitude_e6',
         'ordered_at','captured_at','reservation_expires_at')
SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS order_purchase_records (
 order_id INTEGER PRIMARY KEY REFERENCES orders(id),
 buyer_id INTEGER NOT NULL REFERENCES users(id), farmer_id INTEGER NOT NULL REFERENCES users(id),
 product_id INTEGER NOT NULL REFERENCES products(id), pickup_code TEXT NOT NULL, product_name TEXT NOT NULL,
 unit_price_grosze INTEGER NOT NULL CHECK(typeof(unit_price_grosze)='integer' AND unit_price_grosze>0),
 quantity INTEGER NOT NULL CHECK(typeof(quantity)='integer' AND quantity>0),
 subtotal_grosze INTEGER NOT NULL CHECK(typeof(subtotal_grosze)='integer' AND subtotal_grosze=unit_price_grosze*quantity),
 delivery_grosze INTEGER NOT NULL CHECK(typeof(delivery_grosze)='integer' AND delivery_grosze>=0),
 total_grosze INTEGER NOT NULL CHECK(typeof(total_grosze)='integer' AND total_grosze=subtotal_grosze+delivery_grosze),
 fulfillment TEXT NOT NULL CHECK(fulfillment IN ('odbior','dostawa')),
 pickup_point_id INTEGER, point_name TEXT, point_city TEXT, point_street TEXT, point_opening_hours TEXT,
 latitude_e6 INTEGER CHECK(latitude_e6 BETWEEN -90000000 AND 90000000),
 longitude_e6 INTEGER CHECK(longitude_e6 BETWEEN -180000000 AND 180000000),
 ordered_at TEXT NOT NULL, captured_at TEXT NOT NULL, reservation_expires_at TEXT NOT NULL,
 CHECK((latitude_e6 IS NULL AND longitude_e6 IS NULL) OR (latitude_e6 IS NOT NULL AND longitude_e6 IS NOT NULL)),
 CHECK((fulfillment='odbior' AND pickup_point_id IS NOT NULL AND point_name IS NOT NULL
        AND point_city IS NOT NULL AND point_street IS NOT NULL AND point_opening_hours IS NOT NULL AND delivery_grosze=0)
    OR (fulfillment='dostawa' AND pickup_point_id IS NULL AND point_name IS NULL AND point_city IS NULL
        AND point_street IS NULL AND point_opening_hours IS NULL AND latitude_e6 IS NULL AND longitude_e6 IS NULL))
);
CREATE TRIGGER IF NOT EXISTS purchase_records_no_replace BEFORE INSERT ON order_purchase_records
WHEN EXISTS(SELECT 1 FROM order_purchase_records WHERE order_id=NEW.order_id)
BEGIN SELECT RAISE(ABORT,'Purchase records cannot be replaced'); END;
CREATE TRIGGER IF NOT EXISTS purchase_records_no_update BEFORE UPDATE ON order_purchase_records
BEGIN SELECT RAISE(ABORT,'Purchase records are insert-only'); END;
CREATE TRIGGER IF NOT EXISTS purchase_records_no_delete BEFORE DELETE ON order_purchase_records
BEGIN SELECT RAISE(ABORT,'Purchase records are insert-only'); END;
'''


def capture_purchase(con,order_id):
    """Checkout already holds product/point locks; all writes share its transaction."""
    row=con.execute('''SELECT o.*,p.name AS product_name,p.price_grosze AS unit_price_grosze,
        h.expires_at AS reservation_expires_at,l.pickup_point_id,t.name AS point_name,t.city AS point_city,t.street AS point_street,
        t.opening_hours AS point_opening_hours,c.latitude_e6,c.longitude_e6
        FROM orders o JOIN products p ON p.id=o.product_id JOIN order_locations l ON l.order_id=o.id
        JOIN inventory_reservations h ON h.order_id=o.id
        LEFT JOIN pickup_points t ON t.id=l.pickup_point_id
        LEFT JOIN pickup_point_coordinates c ON c.point_id=t.id WHERE o.id=?''',(order_id,)).fetchone()
    if row is None or row['unit_price_grosze']*row['quantity']!=row['subtotal_grosze']:
        raise ValueError('Nie można potwierdzić pierwotnych warunków zakupu')
    data={key:row[key] for key in COLUMNS if key not in ('order_id','ordered_at','captured_at')}
    data.update(order_id=order_id,ordered_at=row['created_at'],captured_at=datetime.now(timezone.utc).isoformat())
    con.execute('INSERT INTO order_purchase_records('+','.join(COLUMNS)+') VALUES('+','.join('?' for _ in COLUMNS)+')',
                tuple(data[key] for key in COLUMNS))


def record_issues(order,record):
    problems=[]
    for key in ('buyer_id','farmer_id','product_id','pickup_code','quantity','subtotal_grosze','delivery_grosze','total_grosze','fulfillment'):
        if order[key]!=record[key]:problems.append('ORDER_RECORD_'+key.upper()+'_MISMATCH')
    if order['created_at']!=record['ordered_at']:problems.append('ORDER_RECORD_TIMESTAMP_MISMATCH')
    if (any(type(record[k]) is not int for k in ('quantity','unit_price_grosze','subtotal_grosze','delivery_grosze','total_grosze'))
        or record['unit_price_grosze']<=0 or record['quantity']<=0
        or record['unit_price_grosze']*record['quantity']!=record['subtotal_grosze']
        or record['subtotal_grosze']+record['delivery_grosze']!=record['total_grosze']):
        problems.append('INVALID_RECORD_AMOUNT')
    return problems


def original_terms(record):
    point=None
    if record['fulfillment']=='odbior':
        point={'id':record['pickup_point_id'],'name':record['point_name'],'city':record['point_city'],
            'street':record['point_street'],'opening_hours':record['point_opening_hours'],
            'latitude_e6':record['latitude_e6'],'longitude_e6':record['longitude_e6']}
    return {'pickup_code':record['pickup_code'],'ordered_at':record['ordered_at'],'captured_at':record['captured_at'],'reservation_expires_at':record['reservation_expires_at'],
        'product':{'id':record['product_id'],'name':record['product_name'],'unit_price_grosze':record['unit_price_grosze']},
        'quantity':record['quantity'],'subtotal_grosze':record['subtotal_grosze'],
        'delivery_grosze':record['delivery_grosze'],'total_grosze':record['total_grosze'],
        'fulfillment':record['fulfillment'],'pickup_point':point}


def order_record(con,order):
    row=con.execute('SELECT * FROM order_purchase_records WHERE order_id=?',(order['id'],)).fetchone()
    if row is not None and record_issues(order,row):raise ValueError('Zapis zakupu wymaga weryfikacji zgodności')
    if row is not None:
        location=con.execute('SELECT pickup_point_id FROM order_locations WHERE order_id=?',(order['id'],)).fetchone()
        if location is None or location['pickup_point_id']!=row['pickup_point_id']:
            raise ValueError('Zapis miejsca odbioru wymaga weryfikacji zgodności')
    from backend.payment_store import get_payment
    payment=get_payment(con,order['id'])
    return {'order_id':order['id'],'pickup_code':order['pickup_code'],'mode':'test',
        'original_available':row is not None,'original':original_terms(row) if row is not None else None,
        'current':{'status':order['status'],'confirmed_at':order['confirmed_at'],
                   'payment_state_test':payment.state if payment else 'not_initialized_test',
                   'refund_grosze':payment.refund_grosze if payment else 0},
        'notice':('Zapis warunków zakupu testowego. Nie jest fakturą ani potwierdzeniem prawdziwej płatności.' if row is not None
                  else 'Brak zapisu pierwotnych warunków. Nie odtwarzamy ich z bieżącego katalogu ani punktu.')}


def audit_records(con):
    # One SQL statement supplies a consistent database snapshot without customer PII in output.
    rows=con.execute('''SELECT o.id,o.buyer_id,o.farmer_id,o.product_id,o.pickup_code,o.quantity,o.subtotal_grosze,
        o.delivery_grosze,o.total_grosze,o.fulfillment,o.created_at,
        r.order_id AS record_order_id,r.buyer_id AS r_buyer_id,r.farmer_id AS r_farmer_id,
        r.product_id AS r_product_id,r.pickup_code AS r_pickup_code,r.quantity AS r_quantity,r.subtotal_grosze AS r_subtotal_grosze,
        r.delivery_grosze AS r_delivery_grosze,r.total_grosze AS r_total_grosze,r.fulfillment AS r_fulfillment,
        r.ordered_at AS r_ordered_at,r.unit_price_grosze AS r_unit_price_grosze,
        r.pickup_point_id AS r_pickup_point_id,l.order_id AS location_order_id,l.pickup_point_id AS live_pickup_point_id
        FROM orders o LEFT JOIN order_purchase_records r ON r.order_id=o.id LEFT JOIN order_locations l ON l.order_id=o.id ORDER BY o.id''').fetchall()
    issues=[];missing=[]
    for row in rows:
        if row['record_order_id'] is None:missing.append(row['id']);continue
        record={key:row['r_'+key] for key in ('buyer_id','farmer_id','product_id','pickup_code','quantity','subtotal_grosze',
            'delivery_grosze','total_grosze','fulfillment','ordered_at','unit_price_grosze')}
        issues.extend({'order_id':row['id'],'code':code} for code in record_issues(row,record))
        if row['location_order_id'] is None or row['live_pickup_point_id']!=row['r_pickup_point_id']:
            issues.append({'order_id':row['id'],'code':'ORDER_RECORD_LOCATION_MISMATCH'})
    return {'checked_orders':len(rows),'records_present':len(rows)-len(missing),
        'orders_without_original_record':missing,'issues':issues,'consistent':not issues,'complete':not missing,
        'ok':not issues and not missing,'read_only':True,'mode':'test'}
