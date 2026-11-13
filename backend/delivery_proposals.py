"""Versioned seller schedule proposals; buyer consent gates all shipment items."""
import json
import secrets
from datetime import date,datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from fastapi import Depends,Header,HTTPException
from pydantic import BaseModel,Field

SCHEMA='''CREATE TABLE IF NOT EXISTS delivery_schedule_proposals (
 id TEXT PRIMARY KEY,
 anchor_order_id INTEGER NOT NULL REFERENCES orders(id),
 base_revision INTEGER NOT NULL CHECK(base_revision>=0),
 request_revision INTEGER NOT NULL CHECK(request_revision=base_revision+1),
 delivery_date TEXT NOT NULL,
 from_minute INTEGER NOT NULL CHECK(from_minute>=0 AND from_minute<1440),
 to_minute INTEGER NOT NULL CHECK(to_minute>from_minute AND to_minute<=1440),
 member_ids TEXT NOT NULL,
 prior_schedule TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('pending','accepted','declined','superseded')),
 created_at TEXT NOT NULL,
 decided_at TEXT,
 UNIQUE(anchor_order_id,base_revision)
);
CREATE INDEX IF NOT EXISTS delivery_schedule_proposals_anchor ON delivery_schedule_proposals(anchor_order_id,request_revision);
'''

class ProposalIn(BaseModel):
    model_config={'extra':'forbid'}
    revision:int=Field(strict=True,ge=0,le=1000000000)
    delivery_date:str=Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    from_time:str=Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    to_time:str=Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')

class ProposalDecisionIn(BaseModel):
    model_config={'extra':'forbid'}
    decision:str=Field(pattern=r'^(accepted|declined)$')
    revision:int=Field(strict=True,ge=0,le=1000000000)


def group_rows(con,order_id,*,postgres=False):
    link=con.execute('SELECT shipment_id FROM shipment_order_links WHERE order_id=?',(order_id,)).fetchone()
    if link:
        rows=con.execute('SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=? ORDER BY o.id'+(' FOR UPDATE OF o' if postgres else ''),(link['shipment_id'],)).fetchall()
    else:
        rows=con.execute('SELECT * FROM orders WHERE id=?'+(' FOR UPDATE' if postgres else ''),(order_id,)).fetchall()
    return rows


def authorize(rows,user,role):
    key='farmer_id' if role=='rolnik' else 'buyer_id'
    if not rows or any(r[key]!=user['id'] or r['fulfillment']!='dostawa' for r in rows):
        raise HTTPException(404,'Nie znaleziono dostawy')
    if len({(r['buyer_id'],r['farmer_id']) for r in rows})!=1:
        raise HTTPException(409,'Niespójna przesyłka')


def check_pending(con,rows,revision):
    from backend.inventory_reservations import payment_deadline_passed
    from backend.payment_store import get_payment
    stamp=datetime.now(timezone.utc);preferences=[]
    for order in rows:
        preference=con.execute('SELECT * FROM address_delivery_requests WHERE order_id=?',(order['id'],)).fetchone()
        payment=get_payment(con,order['id'])
        if (preference is None or preference['state']!='pending' or preference['revision']!=revision
                or order['status']!='oczekuje_na_platnosc_testowa'
                or payment_deadline_passed(con,order['id'],now=stamp)
                or (payment is not None and payment.state not in ('awaiting_payment','failed_test'))):
            raise HTTPException(409,'Termin lub stan dostawy zmienił się; odśwież dane')
        preferences.append(preference)
    return preferences


def proposal_view(row):
    if row is None:return None
    return {key:row[key] for key in ('id','request_revision','delivery_date','from_minute','to_minute','state')}


def latest(con,order_id):
    link=con.execute('SELECT shipment_id FROM shipment_order_links WHERE order_id=?',(order_id,)).fetchone()
    anchor=con.execute('SELECT MIN(order_id) AS anchor FROM shipment_order_links WHERE shipment_id=?',(link['shipment_id'],)).fetchone()['anchor'] if link else order_id
    return con.execute('SELECT * FROM delivery_schedule_proposals WHERE anchor_order_id=? ORDER BY request_revision DESC LIMIT 1',(anchor,)).fetchone()


def assert_no_pending(con,order_id):
    proposal=latest(con,order_id)
    if proposal is not None and proposal['state']=='pending':
        raise HTTPException(409,'Nowy termin wymaga decyzji klienta')


def register(app,db,write_db,current_user,record_event,*,postgres=False):
    if not postgres:
        with db() as con:con.executescript(SCHEMA)
    def enabled():
        from backend.address_delivery import enabled as active
        if not active():raise HTTPException(503,'Terminy dostaw są wyłączone')

    @app.post('/address-delivery/requests/{order_id}/proposal')
    def propose(order_id:int,payload:ProposalIn,user=Depends(current_user),authorization:str|None=Header(default=None)):
        enabled()
        from backend.address_delivery import minutes
        start,end=minutes(payload.from_time),minutes(payload.to_time)
        if start>=end:raise HTTPException(422,'Początek przedziału musi poprzedzać koniec')
        with write_db(user,authorization,('rolnik',)) as con:
            rows=group_rows(con,order_id,postgres=postgres);authorize(rows,user,'rolnik');anchor=rows[0]['id']
            existing=con.execute('SELECT * FROM delivery_schedule_proposals WHERE anchor_order_id=? AND base_revision=?',(anchor,payload.revision)).fetchone()
            if existing is not None:
                if json.loads(existing['member_ids'])!=[r['id'] for r in rows]:raise HTTPException(409,'Zmienił się skład przesyłki')
                if (existing['delivery_date'],existing['from_minute'],existing['to_minute'])!=(payload.delivery_date,start,end):
                    raise HTTPException(409,'Inna propozycja została już zapisana dla tej wersji')
                return {'proposal':proposal_view(existing),'already_processed':True}
            preferences=check_pending(con,rows,payload.revision)
            try:
                day=date.fromisoformat(payload.delivery_date);now=datetime.now(ZoneInfo('Europe/Warsaw'))
                if not now.date()<=day<=now.date()+timedelta(days=90) or (day==now.date() and start<=now.hour*60+now.minute):raise ValueError()
            except ValueError:raise HTTPException(422,'Wybierz przyszły termin w ciągu 90 dni') from None
            stamp=datetime.now(timezone.utc).isoformat();identifier=secrets.token_hex(16)
            con.execute("UPDATE delivery_schedule_proposals SET state='superseded',decided_at=? WHERE anchor_order_id=? AND state='pending'",(stamp,anchor))
            prior=[{key:p[key] for key in ('order_id','delivery_date','customer_from','customer_to','agreed_from','agreed_to')} for p in preferences]
            con.execute('''INSERT INTO delivery_schedule_proposals(id,anchor_order_id,base_revision,request_revision,delivery_date,
                from_minute,to_minute,member_ids,prior_schedule,state,created_at) VALUES(?,?,?,?,?,?,?,?,?,'pending',?)''',
                (identifier,anchor,payload.revision,payload.revision+1,payload.delivery_date,start,end,json.dumps([r['id'] for r in rows]),json.dumps(prior),stamp))
            for order in rows:
                con.execute('UPDATE address_delivery_requests SET revision=revision+1 WHERE order_id=?',(order['id'],))
                record_event(con,order['id'],user['id'],'delivery_schedule_proposed_test',order['status'],order['status'])
            return {'proposal':proposal_view(con.execute('SELECT * FROM delivery_schedule_proposals WHERE id=?',(identifier,)).fetchone()),'already_processed':False}

    @app.post('/address-delivery/proposals/{proposal_id}/decision')
    def decide(proposal_id:str,payload:ProposalDecisionIn,user=Depends(current_user),authorization:str|None=Header(default=None)):
        enabled()
        with write_db(user,authorization,('klient',)) as con:
            proposal=con.execute('SELECT * FROM delivery_schedule_proposals WHERE id=?',(proposal_id,)).fetchone()
            if proposal is None:raise HTTPException(404,'Nie znaleziono propozycji')
            rows=group_rows(con,proposal['anchor_order_id'],postgres=postgres);authorize(rows,user,'klient')
            proposal=con.execute('SELECT * FROM delivery_schedule_proposals WHERE id=?'+(' FOR UPDATE' if postgres else ''),(proposal_id,)).fetchone()
            if proposal['request_revision']!=payload.revision or json.loads(proposal['member_ids'])!=[r['id'] for r in rows]:
                raise HTTPException(409,'Propozycja jest nieaktualna')
            if proposal['state']==payload.decision:return {'state':payload.decision,'already_processed':True}
            if proposal['state']!='pending':raise HTTPException(409,'Propozycja została już rozstrzygnięta lub zastąpiona')
            check_pending(con,rows,payload.revision)
            if payload.decision=='accepted':
                now=datetime.now(ZoneInfo('Europe/Warsaw'));day=date.fromisoformat(proposal['delivery_date'])
                if day<now.date() or (day==now.date() and proposal['from_minute']<=now.hour*60+now.minute):
                    raise HTTPException(409,'Proponowany termin już się rozpoczął; poproś o nową propozycję')
            for order in rows:
                if payload.decision=='accepted':
                    con.execute("""UPDATE address_delivery_requests SET state='accepted',delivery_date=?,customer_from=?,customer_to=?,
                        agreed_from=?,agreed_to=?,revision=revision+1 WHERE order_id=?""",
                        (proposal['delivery_date'],proposal['from_minute'],proposal['to_minute'],proposal['from_minute'],proposal['to_minute'],order['id']))
                else:
                    # Rejection retains the original pending request; no payment or refund.
                    con.execute('UPDATE address_delivery_requests SET revision=revision+1 WHERE order_id=?',(order['id'],))
                record_event(con,order['id'],user['id'],'delivery_schedule_'+payload.decision+'_test',order['status'],order['status'])
            con.execute('UPDATE delivery_schedule_proposals SET state=?,decided_at=? WHERE id=?',(payload.decision,datetime.now(timezone.utc).isoformat(),proposal_id))
        return {'state':payload.decision,'already_processed':False}
