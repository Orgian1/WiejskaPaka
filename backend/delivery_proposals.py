"""Revised delivery times: seller proposes, buyer explicitly accepts, under order locks."""
from datetime import datetime, timedelta, date, timezone
from zoneinfo import ZoneInfo
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field
from backend.address_delivery import minutes, DecisionIn, enabled
from backend.inventory_reservations import payment_deadline_passed
from backend.payment_store import get_payment

SCHEMA_SQLITE = '''
CREATE TABLE IF NOT EXISTS delivery_time_proposals (
 order_id INTEGER NOT NULL REFERENCES orders(id), revision INTEGER NOT NULL CHECK(revision>=1),
 delivery_date TEXT NOT NULL, start_minute INTEGER NOT NULL, end_minute INTEGER NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','accepted','declined')),
 PRIMARY KEY(order_id,revision),
 CHECK(start_minute>=0 AND end_minute<=1439 AND start_minute<end_minute)
);
'''


class ProposalIn(BaseModel):
    model_config = {'extra': 'forbid'}
    revision: int = Field(strict=True, ge=0)
    delivery_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    from_time: str = Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
    to_time: str = Field(pattern=r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')


def latest(con, order_id, revision):
    row = con.execute('SELECT revision,delivery_date,start_minute,end_minute,state FROM delivery_time_proposals WHERE order_id=? AND revision=?', (order_id,revision)).fetchone()
    return dict(row) if row else None


def register(app, order_write_db, current_user, record_event, *, postgres=False):
    def rows_for(con, order_id, user, role):
        if not enabled():
            raise HTTPException(503, 'Terminy dostaw są wyłączone')
        link = con.execute('SELECT shipment_id FROM shipment_order_links WHERE order_id=?', (order_id,)).fetchone()
        if link:
            rows = con.execute('SELECT o.* FROM orders o JOIN shipment_order_links l ON l.order_id=o.id WHERE l.shipment_id=? ORDER BY o.id'+(' FOR UPDATE OF o' if postgres else ''), (link['shipment_id'],)).fetchall()
        else:
            rows = con.execute('SELECT * FROM orders WHERE id=?'+(' FOR UPDATE' if postgres else ''), (order_id,)).fetchall()
        key = 'farmer_id' if role == 'rolnik' else 'buyer_id'
        if not rows or any(r[key]!=user['id'] or r['fulfillment']!='dostawa' for r in rows):
            raise HTTPException(404, 'Nie znaleziono dostawy')
        if any((r['buyer_id'],r['farmer_id'])!=(rows[0]['buyer_id'],rows[0]['farmer_id']) for r in rows):
            raise HTTPException(409, 'Niespójna przesyłka')
        prefs = [con.execute('SELECT * FROM address_delivery_requests WHERE order_id=?',(r['id'],)).fetchone() for r in rows]
        if any(p is None for p in prefs):
            raise HTTPException(409, 'Brak danych terminu dostawy')
        return rows, prefs

    def require_open(con, rows, prefs, revision):
        now = datetime.now(timezone.utc)
        for r,p in zip(rows,prefs):
            payment = get_payment(con,r['id'])
            if (p['state']!='pending' or p['revision']!=revision or r['status']!='oczekuje_na_platnosc_testowa'
                or payment_deadline_passed(con,r['id'],now=now)
                or (payment is not None and payment.state not in ('awaiting_payment','failed_test'))):
                raise HTTPException(409, 'Termin zmienił się, rezerwacja wygasła lub zamówienie jest już opłacone. Odśwież widok.')

    @app.post('/address-delivery/requests/{order_id}/proposals')
    def propose(order_id:int,payload:ProposalIn,user=Depends(current_user),authorization:str|None=Header(default=None)):
        try:
            day=date.fromisoformat(payload.delivery_date)
            start,end=minutes(payload.from_time),minutes(payload.to_time)
            now=datetime.now(timezone.utc).astimezone(ZoneInfo('Europe/Warsaw'))
            if not now.date()<=day<=now.date()+timedelta(days=90) or start>=end or (day==now.date() and start<=now.hour*60+now.minute):
                raise ValueError()
        except ValueError:
            raise HTTPException(422,'Podaj przyszły termin i poprawny zakres godzin') from None
        with order_write_db(user,authorization,('rolnik',)) as con:
            rows,prefs=rows_for(con,order_id,user,'rolnik')
            # Retry of the identical proposal is safe even after a lost response.
            old=[latest(con,r['id'],payload.revision+1) for r in rows]
            if all(p and p['delivery_date']==payload.delivery_date and p['start_minute']==start and p['end_minute']==end and q['revision']==payload.revision+1 for p,q in zip(old,prefs)):
                return {'revision':payload.revision+1,'already_processed':True}
            require_open(con,rows,prefs,payload.revision)
            for r in rows:
                con.execute('INSERT INTO delivery_time_proposals(order_id,revision,delivery_date,start_minute,end_minute) VALUES(?,?,?,?,?)',(r['id'],payload.revision+1,payload.delivery_date,start,end))
                con.execute('UPDATE address_delivery_requests SET revision=revision+1 WHERE order_id=?',(r['id'],))
                record_event(con,r['id'],user['id'],'address_delivery_proposed',r['status'],r['status'])
        return {'revision':payload.revision+1,'already_processed':False}

    @app.post('/address-delivery/requests/{order_id}/proposal-decision')
    def respond(order_id:int,payload:DecisionIn,user=Depends(current_user),authorization:str|None=Header(default=None)):
        with order_write_db(user,authorization,('klient',)) as con:
            rows,prefs=rows_for(con,order_id,user,'klient')
            proposals=[latest(con,r['id'],payload.revision) for r in rows]
            if any(p is None for p in proposals):
                raise HTTPException(409,'Nie znaleziono propozycji. Odśwież widok.')
            if all(p['state']==payload.decision and q['revision']==payload.revision+1 for p,q in zip(proposals,prefs)):
                return {'state':payload.decision,'already_processed':True}
            require_open(con,rows,prefs,payload.revision)
            if any(p['state']!='pending' for p in proposals):
                raise HTTPException(409,'Propozycja została już rozstrzygnięta')
            for r,p in zip(rows,proposals):
                if payload.decision=='accepted':
                    instant=datetime.now(timezone.utc).astimezone(ZoneInfo('Europe/Warsaw'))
                    day=date.fromisoformat(p['delivery_date'])
                    if day<instant.date() or (day==instant.date() and p['start_minute']<=instant.hour*60+instant.minute):
                        raise HTTPException(409,'Proponowany termin już minął')
                    con.execute("UPDATE address_delivery_requests SET delivery_date=?,customer_from=?,customer_to=?,agreed_from=?,agreed_to=?,state='accepted',revision=revision+1 WHERE order_id=?",(p['delivery_date'],p['start_minute'],p['end_minute'],p['start_minute'],p['end_minute'],r['id']))
                else:
                    con.execute('UPDATE address_delivery_requests SET revision=revision+1 WHERE order_id=?',(r['id'],))
                con.execute('UPDATE delivery_time_proposals SET state=? WHERE order_id=? AND revision=?',(payload.decision,r['id'],payload.revision))
                record_event(con,r['id'],user['id'],'address_delivery_proposal_'+payload.decision,r['status'],r['status'])
        return {'state':payload.decision,'already_processed':False}
