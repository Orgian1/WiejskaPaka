"""Private test-only purchase cases. No order, inventory or money mutations."""
from datetime import datetime, timezone
from uuid import uuid4

SCHEMA = '''
CREATE TABLE IF NOT EXISTS support_cases (
 id TEXT PRIMARY KEY, buyer_id INTEGER NOT NULL REFERENCES users(id),
 farmer_id INTEGER NOT NULL REFERENCES users(id),
 order_id INTEGER REFERENCES orders(id), shipment_id TEXT REFERENCES shipment_groups(id),
 request_id TEXT NOT NULL,
 category TEXT NOT NULL CHECK(category IN ('product','pickup','delivery','other')),
 description TEXT NOT NULL CHECK(length(description) BETWEEN 10 AND 2000),
 status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','in_review','closed_test')),
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 CHECK((order_id IS NOT NULL AND shipment_id IS NULL) OR (order_id IS NULL AND shipment_id IS NOT NULL)),
 UNIQUE(buyer_id,request_id)
);
CREATE INDEX IF NOT EXISTS support_cases_buyer_idx ON support_cases(buyer_id,created_at,id);
CREATE INDEX IF NOT EXISTS support_cases_farmer_idx ON support_cases(farmer_id,created_at,id);
CREATE TABLE IF NOT EXISTS support_case_events (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES support_cases(id),
 actor_id INTEGER NOT NULL REFERENCES users(id),
 actor_role TEXT NOT NULL CHECK(actor_role IN ('klient','rolnik','admin')),
 request_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
 message TEXT NOT NULL CHECK(length(message)<=2000),
 requested_status TEXT CHECK(requested_status IN ('in_review','closed_test')),
 status_after TEXT NOT NULL CHECK(status_after IN ('new','in_review','closed_test')),
 created_at TEXT NOT NULL,
 UNIQUE(case_id,actor_id,request_id), UNIQUE(case_id,revision)
);
'''
NOTICE='Zgłoszenie testowe. Wpis ani zamknięcie sprawy nie zmienia zakupu, magazynu ani rozliczeń i nie wykonuje zwrotu.'

class CaseError(ValueError):
    def __init__(self,status,message):
        super().__init__(message);self.status=status


def scope(user):
    if user['role']=='admin':return '1=1',()
    if user['role']=='klient':return 'buyer_id=?',(user['id'],)
    if user['role']=='rolnik':return 'farmer_id=?',(user['id'],)
    raise CaseError(403,'Brak uprawnień do zgłoszeń')


def visible(con,case_id,user,*,lock=False):
    condition,params=scope(user)
    row=con.execute('SELECT * FROM support_cases WHERE id=? AND '+condition+(' FOR UPDATE' if lock else ''),(case_id,*params)).fetchone()
    if row is None:raise CaseError(404,'Nie znaleziono zgłoszenia')
    return dict(row)


def projection(row,*,details=False):
    keys=('id','category','status','revision','created_at','updated_at')
    result={key:row[key] for key in keys}
    result.update(kind='shipment' if row['shipment_id'] is not None else 'order',target_id=row['shipment_id'] or str(row['order_id']))
    if details:result['description']=row['description']
    return result


def detail(con,case_id,user,*,before_revision=None):
    row=visible(con,case_id,user)
    before=row['revision']+1 if before_revision is None else before_revision
    events=con.execute('''SELECT revision,actor_role,message,status_after,created_at
        FROM support_case_events WHERE case_id=? AND revision<? ORDER BY revision DESC LIMIT 20''',(case_id,before)).fetchall()
    events=[dict(event) for event in reversed(events)]
    return {'mode':'test','case':projection(row,details=True),'events':events,
            'has_older_events':bool(events and events[0]['revision']>1),'notice':NOTICE}


def listing(con,user,*,status=None,limit=20,offset=0):
    condition,params=scope(user)
    if type(limit) is not int or not 1<=limit<=50 or type(offset) is not int or not 0<=offset<=10000:
        raise CaseError(422,'Nieprawidłowa strona zgłoszeń')
    if status is not None:
        if status not in ('new','in_review','closed_test'):raise CaseError(422,'Nieprawidłowy stan zgłoszenia')
        condition+=' AND status=?';params=(*params,status)
    rows=con.execute('SELECT * FROM support_cases WHERE '+condition+' ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?',(*params,limit+1,offset)).fetchall()
    return {'mode':'test','cases':[projection(row) for row in rows[:limit]],'limit':limit,'offset':offset,'has_more':len(rows)>limit,'notice':NOTICE}


def target(con,kind,target_id,user):
    if kind=='order':
        if not target_id.isascii() or not target_id.isdigit() or not 0<int(target_id)<2**63:raise CaseError(404,'Nie znaleziono zakupu')
        row=con.execute('SELECT id,buyer_id,farmer_id FROM orders WHERE id=? AND buyer_id=?',(int(target_id),user['id'])).fetchone()
        if row is None:raise CaseError(404,'Nie znaleziono zakupu')
        linked=con.execute('SELECT shipment_id FROM shipment_order_links WHERE order_id=?',(row['id'],)).fetchone()
        if linked:return target(con,'shipment',linked['shipment_id'],user)
        return row['id'],None,row['farmer_id']
    if kind!='shipment':raise CaseError(422,'Nieprawidłowy rodzaj zakupu')
    row=con.execute('SELECT id,buyer_id,farmer_id FROM shipment_groups WHERE id=? AND buyer_id=?',(target_id,user['id'])).fetchone()
    if row is None:raise CaseError(404,'Nie znaleziono zakupu')
    items=con.execute('SELECT o.buyer_id,o.farmer_id FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=?',(row['id'],)).fetchall()
    if not items or any(o['buyer_id']!=row['buyer_id'] or o['farmer_id']!=row['farmer_id'] for o in items):raise CaseError(409,'Niespójna przesyłka')
    return None,row['id'],row['farmer_id']


def create(con,user,kind,target_id,category,description,request_id,*,postgres=False):
    if user['role']!='klient':raise CaseError(403,'Tylko kupujący może utworzyć zgłoszenie')
    if category not in ('product','pickup','delivery','other') or not isinstance(description,str) or not 10<=len(description.strip())<=2000:raise CaseError(422,'Nieprawidłowa treść zgłoszenia')
    description=description.strip()
    if postgres:con.execute('SELECT id FROM users WHERE id=? FOR UPDATE',(user['id'],)).fetchone()
    order_id,shipment_id,farmer_id=target(con,kind,target_id,user)
    prior=con.execute('SELECT * FROM support_cases WHERE buyer_id=? AND request_id=?',(user['id'],request_id)).fetchone()
    if prior:
        if (prior['order_id'],prior['shipment_id'],prior['category'],prior['description'])!=(order_id,shipment_id,category,description):raise CaseError(409,'Identyfikator zgłoszenia został użyty dla innej treści')
        return detail(con,prior['id'],user)
    case_id=uuid4().hex;now=datetime.now(timezone.utc).isoformat()
    con.execute('''INSERT INTO support_cases(id,buyer_id,farmer_id,order_id,shipment_id,request_id,category,description,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)''',(case_id,user['id'],farmer_id,order_id,shipment_id,request_id,category,description,now,now))
    con.execute('''INSERT INTO support_case_events(id,case_id,actor_id,actor_role,request_id,revision,message,status_after,created_at)
        VALUES(?,?,?,?,?,1,'','new',?)''',(uuid4().hex,case_id,user['id'],'klient',request_id,now))
    return detail(con,case_id,user)


def reply(con,case_id,user,message,request_id,expected_revision,status=None,*,postgres=False):
    row=visible(con,case_id,user,lock=postgres)
    if not isinstance(message,str) or not 1<=len(message.strip())<=2000 or type(expected_revision) is not int or expected_revision<1:raise CaseError(422,'Nieprawidłowa odpowiedź')
    message=message.strip()
    if status is not None and (user['role']!='admin' or status not in ('in_review','closed_test')):raise CaseError(403,'Tylko administrator zmienia stan obsługi')
    prior=con.execute('SELECT message,requested_status FROM support_case_events WHERE case_id=? AND actor_id=? AND request_id=?',(case_id,user['id'],request_id)).fetchone()
    if prior:
        if (prior['message'],prior['requested_status'])!=(message,status):raise CaseError(409,'Identyfikator odpowiedzi został użyty dla innej treści')
        return detail(con,case_id,user)
    if row['revision']!=expected_revision:raise CaseError(409,'Zgłoszenie zmieniło się. Odśwież historię przed odpowiedzią.')
    if row['status']=='closed_test' and not (user['role']=='admin' and status=='in_review'):raise CaseError(409,'Zgłoszenie jest zamknięte testowo; ponowne otwarcie wymaga administratora')
    now=datetime.now(timezone.utc).isoformat();next_status=status or row['status'];revision=row['revision']+1
    changed=con.execute('UPDATE support_cases SET status=?,revision=?,updated_at=? WHERE id=? AND revision=?',(next_status,revision,now,case_id,expected_revision))
    if changed.rowcount!=1:raise CaseError(409,'Zgłoszenie zmieniło się. Odśwież historię.')
    con.execute('''INSERT INTO support_case_events(id,case_id,actor_id,actor_role,request_id,revision,message,requested_status,status_after,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)''',(uuid4().hex,case_id,user['id'],user['role'],request_id,revision,message,status,next_status,now))
    return detail(con,case_id,user)
