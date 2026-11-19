"""Text-only marketplace advertising slots; independent from wallet interstitials."""
import secrets
from datetime import datetime, timezone
from typing import Literal
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict

SCHEMA = """
CREATE TABLE IF NOT EXISTS marketplace_ad_campaigns (
 id TEXT PRIMARY KEY,
 slot TEXT NOT NULL CHECK(slot IN ('login','buyer','seller')),
 title TEXT NOT NULL,
 body TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
 starts_at BIGINT NOT NULL,
 ends_at BIGINT NOT NULL,
 CHECK(ends_at>starts_at)
);
CREATE INDEX IF NOT EXISTS marketplace_ad_active_idx
 ON marketplace_ad_campaigns(slot,enabled,starts_at,ends_at);
"""

class CampaignIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    slot: Literal['login','buyer','seller']
    title: str=Field(min_length=1,max_length=100)
    body: str=Field(min_length=1,max_length=500)
    enabled: bool=False
    starts_at: int=Field(ge=0)
    ends_at: int=Field(ge=1)

def validate(payload):
    if (not payload.title.strip() or not payload.body.strip()
            or any(ord(char)<32 and char not in (chr(10), chr(9)) for char in payload.title+payload.body)
            or payload.ends_at<=payload.starts_at):
        raise HTTPException(422,'Nieprawidłowa treść lub okres kampanii')

def current(con,slot,now=None):
    if slot not in ('login','buyer','seller'):
        raise HTTPException(404,'Nieznane miejsce reklamowe')
    now=int(datetime.now(timezone.utc).timestamp()) if now is None else now
    row=con.execute("""SELECT id,title,body FROM marketplace_ad_campaigns
      WHERE slot=? AND enabled=1 AND starts_at<=? AND ends_at>?
      ORDER BY starts_at DESC,id DESC LIMIT 1""",(slot,now,now)).fetchone()
    return dict(row) if row else None

def install(app,db,write_db,current_user,database_url):
    if not database_url:
        with db() as con: con.executescript(SCHEMA)
    else:
        with db() as con: con.execute('SELECT id FROM marketplace_ad_campaigns LIMIT 0')

    @app.get('/ads/slots/{slot}')
    def public_campaign(slot:str):
        with db() as con:return {'campaign':current(con,slot)}

    @app.get('/admin/ads/slots')
    def list_campaigns(user=Depends(current_user)):
        if user['role']!='admin':raise HTTPException(403,'Brak uprawnień')
        with db() as con:
            return {'items':[dict(r) for r in con.execute(
                'SELECT * FROM marketplace_ad_campaigns ORDER BY starts_at DESC,id DESC LIMIT 200').fetchall()]}

    @app.post('/admin/ads/slots',status_code=201)
    def create_campaign(payload:CampaignIn,authorization:str=Header(default=''),user=Depends(current_user)):
        if user['role']!='admin':raise HTTPException(403,'Brak uprawnień')
        validate(payload)
        campaign_id=secrets.token_hex(16)
        with write_db(user,authorization,('admin',)) as con:
            con.execute('INSERT INTO marketplace_ad_campaigns VALUES(?,?,?,?,?,?,?)',
                (campaign_id,payload.slot,payload.title.strip(),payload.body.strip(),
                 int(payload.enabled),payload.starts_at,payload.ends_at))
        return {'id':campaign_id}

    @app.put('/admin/ads/slots/{campaign_id}')
    def update_campaign(campaign_id:str,payload:CampaignIn,authorization:str=Header(default=''),user=Depends(current_user)):
        if user['role']!='admin':raise HTTPException(403,'Brak uprawnień')
        validate(payload)
        with write_db(user,authorization,('admin',)) as con:
            row=con.execute('SELECT id FROM marketplace_ad_campaigns WHERE id=?',(campaign_id,)).fetchone()
            if not row:raise HTTPException(404,'Nie znaleziono kampanii')
            con.execute('UPDATE marketplace_ad_campaigns SET slot=?,title=?,body=?,enabled=?,starts_at=?,ends_at=? WHERE id=?',
                (payload.slot,payload.title.strip(),payload.body.strip(),int(payload.enabled),
                 payload.starts_at,payload.ends_at,campaign_id))
        return {'id':campaign_id}

    @app.delete('/admin/ads/slots/{campaign_id}')
    def disable_campaign(campaign_id:str,authorization:str=Header(default=''),user=Depends(current_user)):
        if user['role']!='admin':raise HTTPException(403,'Brak uprawnień')
        with write_db(user,authorization,('admin',)) as con:
            row=con.execute('SELECT id FROM marketplace_ad_campaigns WHERE id=?',(campaign_id,)).fetchone()
            if not row:raise HTTPException(404,'Nie znaleziono kampanii')
            con.execute('UPDATE marketplace_ad_campaigns SET enabled=0 WHERE id=?',(campaign_id,))
        return {'ok':True}
